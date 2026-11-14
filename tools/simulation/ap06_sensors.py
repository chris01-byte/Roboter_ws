"""Finite cone models; unchanged installed VL53 producer decisions over raw frames."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace, MethodType
import numpy as np
import yaml
from ament_index_python.packages import get_package_share_directory
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from robot_interfaces.msg import NearFieldStatus
from vl53_near_field import measurement_quality


def directions(azimuth, elevation):
    az, el = np.meshgrid(azimuth, elevation)
    return np.column_stack((np.cos(el.ravel())*np.cos(az.ravel()),
                            np.cos(el.ravel())*np.sin(az.ravel()), np.sin(el.ravel())))


def vl53_producer(node, world, publishers):
    # Use the original installed computational methods without importing or
    # instantiating the USB/I2C driver. Only _get_data_safe is the model endpoint.
    path = Path(measurement_quality.__file__).with_name('vl53_near_field_node.py')
    cls = next(n for n in ast.parse(path.read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == 'Vl53NearField')
    names = {'_build_matrix', '_matrix_to_cloud', '_matrix_to_costmap_cloud', '_nanmin', '_tick'}
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = dict(np=np, math=math, Header=Header, point_cloud2=point_cloud2,
                     NearFieldStatus=NearFieldStatus, assess_frame=measurement_quality.assess_frame)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    config = yaml.safe_load((Path(get_package_share_directory('vl53_near_field'))/
                            'config/vl53_params.yaml').read_text())['vl53_near_field']['ros__parameters']
    p = SimpleNamespace(GR=config['grid_r'], GC=config['grid_c'], fov=config['fov_deg'],
        z_min=config['z_min'], z_max=config['z_max'], thresh=config['thresh_m'], inner=config['inner_cols'],
        require_nb=config['require_nb_target'], valid_statuses=config['valid_statuses'],
        min_sps=config['min_signal_per_spad'], max_sigma=config['max_sigma_mm'],
        flipx_left=config['flipx_left'], flipx_right=config['flipx_right'],
        frame_left=config['frame_left'], frame_right=config['frame_right'],
        publish_costmap_cloud=True, costmap_clear_range=.60,
        ch_left=0, ch_right=1, sL=None, sR=None, get_clock=node.get_clock, **publishers)
    p.col_az = np.radians([-(-p.fov/2+(c+.5)/p.GC*p.fov) for c in range(p.GC)])
    p.row_el = np.radians([(-p.fov/2+(r+.5)/p.GR*p.fov) for r in range(p.GR)])
    rays = directions(p.col_az, p.row_el)
    def frame(_sensor, channel):
        matrix = world.cone_returns((.290, .095 if channel == 0 else -.095, .215), rays).reshape(p.GR,p.GC)
        # Invert exactly the raw-index reversal and the calibrated left flip.
        if p.flipx_left if channel == 0 else p.flipx_right:
            matrix = matrix[:, ::-1]
        raw = matrix[::-1, ::-1].ravel()
        valid = np.isfinite(raw)
        return dict(distance_mm=np.where(valid, np.rint(raw*1000), 0).tolist(),
                    target_status=np.where(valid, 5, 255).tolist(),
                    nb_target_detected=valid.astype(int).tolist(), sigma_mm=[10.]*len(raw))
    p._get_data_safe = frame
    for name in names:
        function = namespace[name]
        setattr(p, name, function.__func__ if isinstance(function, staticmethod) else MethodType(function, p))
    return p


def oak_cloud(world, stamp):
    # Declared coarse noiseless pinhole model, original mounting pose. It does
    # not qualify USB/depth calibration, texture failures or real OAK density.
    local = directions(np.radians(np.linspace(-34.7,34.7,16)),
                       np.radians(np.linspace(-27.,27.,8)))
    pitch=.3306; c,s=math.cos(pitch),math.sin(pitch)
    rotation=np.array([[c,0.,s],[0.,1.,0.],[-s,0.,c]])
    distances=world.cone_returns((.15,0.,1.25), local@rotation.T)
    points=(local*distances[:,None])[np.isfinite(distances)]
    return point_cloud2.create_cloud_xyz32(Header(stamp=stamp, frame_id='ap06_camera_frame'), points.tolist())
