"""Built native sweep agrees with the complete NumPy guard and fails closed."""
import importlib.util
import math
from pathlib import Path
import sysconfig

import numpy as np
import pytest
from ament_index_python.packages import get_package_prefix
import explore.metric_frontier as geometry
from test_metric_motion_geometry import door_inputs


@pytest.fixture
def native(monkeypatch):
    # Registered colcon pytest runs from the source package directory. Load
    # the ACTUAL current build explicitly, never silently test only fallback.
    prefix = Path(get_package_prefix('explore'))
    files = list(prefix.rglob('_reserved_sweep'+sysconfig.get_config_var('EXT_SUFFIX')))
    assert len(files)==1, 'current Explore build must provide the native kernel'
    spec = importlib.util.spec_from_file_location('explore._reserved_sweep',files[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(geometry,'_reserved_sweep',module)
    return module


@pytest.mark.parametrize('origin_yaw',[0.,.17,-.42])
@pytest.mark.parametrize('reserve',[(0.,0.),(.05,.02),(.4,.15)])
@pytest.mark.parametrize('count',[1,3,40])
def test_built_native_preserves_entire_reserved_union(native,origin_yaw,reserve,count):
    node,inputs=door_inputs(.68,.02);grid=inputs[0]
    grid.info.origin.orientation.z=math.sin(origin_yaw/2)
    grid.info.origin.orientation.w=math.cos(origin_yaw/2)
    rng=np.random.default_rng(61006)
    for index in range(30):
        mask=(rng.random(inputs[3].shape)>.001) if index%3 else np.ones(inputs[3].shape,bool)
        if index%5==0:mask=mask[:,::-1]
        poses=np.column_stack((rng.uniform(-2.,2.,count),rng.uniform(-.65,.65,count),
                               rng.uniform(-math.pi,math.pi,count)))
        args=(poses,grid,mask,node._world_to_grid,node._metric_bounds,*reserve)
        assert geometry.footprint_poses_clear(*args) == geometry._footprint_poses_clear_numpy(*args)


@pytest.mark.parametrize('available',[False,True])
def test_optional_kernel_and_unsupported_mask_keep_previous_rejection(native,monkeypatch,available):
    node,inputs=door_inputs(.68,.02);grid=inputs[0]
    mask=inputs[3].astype(np.int8);pose=[(.2,0.,0.)]
    col,row=node._world_to_grid(.2,0.,grid.info);mask[row,col]=0
    if not available:monkeypatch.setattr(geometry,'_reserved_sweep',None)
    assert not geometry.footprint_poses_clear(pose,grid,mask,node._world_to_grid,node._metric_bounds)


def buffers():
    res=.1;reserve=res/math.sqrt(2)+.01
    left,right,bottom,top=(-.13,.33,-.25,.25)
    radius=math.hypot(right+reserve,top+reserve)
    radius=radius*(1+64*np.finfo(float).eps)+1e-12
    return [np.zeros((1,3)),np.full((1,2),10,dtype=np.int64),np.ones((1,1)),
            np.zeros((1,1)),np.ones((20,20),bool),
            np.asarray([res,-1.,-1.,1.,0.,radius**2,left-reserve,right+reserve,
                        bottom-reserve,top+reserve,math.ceil(radius/res)+2])]


@pytest.mark.parametrize('change', ['poses_shape','centers_type','angles_shape','empty_angles',
                                    'mask_type','parameters_shape'])
def test_native_rejects_malformed_buffers(native,change):
    args=buffers()
    if change=='poses_shape':args[0]=np.zeros((1,2))
    elif change=='centers_type':args[1]=np.zeros((1,2))
    elif change=='angles_shape':args[3]=np.zeros((2,1))
    elif change=='empty_angles':args[2]=args[3]=np.zeros((1,0))
    elif change=='mask_type':args[4]=np.ones((20,20),np.int8)
    elif change=='parameters_shape':args[5]=np.zeros(10)
    with pytest.raises(TypeError,match='buffer_contract'):native.clear(*args)


@pytest.mark.parametrize('field',['pose','cosine','sine','parameter'])
def test_native_nonfinite_input_never_becomes_clear(native,field):
    args=buffers()
    if field=='pose':args[0][0,0]=math.nan
    elif field=='cosine':args[2][0,0]=math.nan
    elif field=='sine':args[3][0,0]=math.inf
    else:args[5][0]=math.nan
    with pytest.raises(ValueError):native.clear(*args)
