/* Same reserved cell-centre union as metric_frontier.py.
 * NumPy supplies the identical angle coefficients; no FMA/fast-math.
 * The caller owns all source, scope, policy and movement checks. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

static double value(const Py_buffer *b, Py_ssize_t i, Py_ssize_t j) {
    double x;
    memcpy(&x, (char *)b->buf+i*b->strides[0]+(b->ndim==2?j*b->strides[1]:0),sizeof x);
    return x;
}
static int64_t center(const Py_buffer *b, Py_ssize_t i, Py_ssize_t j) {
    int64_t x;memcpy(&x,(char *)b->buf+i*b->strides[0]+j*b->strides[1],sizeof x);return x;
}
static PyObject *clear(PyObject *self, PyObject *args) {
    PyObject *objects[6];Py_buffer b[6]={0};int acquired=0;
    if (!PyArg_ParseTuple(args,"OOOOOO",&objects[0],&objects[1],&objects[2],&objects[3],&objects[4],&objects[5])) return NULL;
    for(int k=0;k<6;k++) {
        if(PyObject_GetBuffer(objects[k],&b[k],PyBUF_FORMAT|PyBUF_STRIDES)<0)goto failed;
        acquired++;
        if (!b[k].format || (b[k].suboffsets != NULL)) {
            PyErr_SetString(PyExc_TypeError,"reserved_sweep_buffer_contract");goto failed;
        }
    }
    if(b[0].ndim!=2||b[0].shape[1]!=3||b[0].itemsize!=8||strcmp(b[0].format,"d")||
       b[1].ndim!=2||b[1].shape[0]!=b[0].shape[0]||b[1].shape[1]!=2||b[1].itemsize!=8||
       (strcmp(b[1].format,"q")&&strcmp(b[1].format,"l"))||
       b[2].ndim!=2||b[2].shape[0]!=b[0].shape[0]||b[2].shape[1]<1||b[2].itemsize!=8||strcmp(b[2].format,"d")||
       b[3].ndim!=2||b[3].shape[0]!=b[0].shape[0]||b[3].shape[1]!=b[2].shape[1]||b[3].itemsize!=8||strcmp(b[3].format,"d")||
       b[4].ndim!=2||b[4].itemsize!=1||strcmp(b[4].format,"?")||
       b[5].ndim!=1||b[5].shape[0]!=11||b[5].itemsize!=8||strcmp(b[5].format,"d")) {
        PyErr_SetString(PyExc_TypeError,"reserved_sweep_buffer_contract");goto failed;
    }
    double p[11];for(int k=0;k<11;k++) {
        p[k]=value(&b[5],k,0);
        if(!isfinite(p[k])) {PyErr_SetString(PyExc_ValueError,"reserved_sweep_parameters_invalid");goto failed;}
    }
    if(p[0]<=0||p[5]<0||p[10]<0||p[10]>100000||floor(p[10])!=p[10]) {
        PyErr_SetString(PyExc_ValueError,"reserved_sweep_parameters_invalid");goto failed;
    }
    int64_t n=(int64_t)p[10];
    for(Py_ssize_t i=0;i<b[0].shape[0];i++) {
        for(int j=0;j<3;j++)if(!isfinite(value(&b[0],i,j))) {
            PyErr_SetString(PyExc_ValueError,"reserved_sweep_pose_invalid");goto failed;
        }
        for(Py_ssize_t h=0;h<b[2].shape[1];h++) {
            if(!isfinite(value(&b[2],i,h)) || !isfinite(value(&b[3],i,h))) {
                PyErr_SetString(PyExc_ValueError,"reserved_sweep_angles_invalid");goto failed;
            }
        }
        for(int j=0;j<2;j++) {
            int64_t c=center(&b[1],i,j);
            if(c<INT64_MIN+n||c>INT64_MAX-n-1) {PyErr_SetString(PyExc_ValueError,"reserved_sweep_center_overflow");goto failed;}
        }
    }
    int result=1;
    Py_BEGIN_ALLOW_THREADS
    for(Py_ssize_t i=0;i<b[0].shape[0]&&result;i++) {
        int64_t c0=center(&b[1],i,0),r0=center(&b[1],i,1);
        double x=value(&b[0],i,0),y=value(&b[0],i,1);
        for(int64_t r=r0-n;r<=r0+n&&result;r++) {
            for(int64_t c=c0-n;c<=c0+n&&result;c++) {
                if(r>=0&&c>=0&&r<b[4].shape[0]&&c<b[4].shape[1]&&
                   *((unsigned char *)b[4].buf+r*b[4].strides[0]+c*b[4].strides[1]))continue;
                double lx=((double)c+.5)*p[0],ly=((double)r+.5)*p[0];
                double dx=p[1]+p[3]*lx-p[4]*ly-x,dy=p[2]+p[4]*lx+p[3]*ly-y;
                if(!(dx*dx+dy*dy<=p[5]))continue;
                for(Py_ssize_t h=0;h<b[2].shape[1];h++) {
                    double co=value(&b[2],i,h),si=value(&b[3],i,h);
                    double bx=co*dx+si*dy,by=-si*dx+co*dy;
                    if(p[6]<=bx&&bx<=p[7]&&p[8]<=by&&by<=p[9]) {result=0;break;}
                }
            }
        }
    }
    Py_END_ALLOW_THREADS
    for(int k=0;k<acquired;k++)PyBuffer_Release(&b[k]);
    return PyBool_FromLong(result);
failed:
    for(int k=0;k<acquired;k++)PyBuffer_Release(&b[k]);
    return NULL;
}
/* Exact point/segment arithmetic used by the NumPy cell-distance oracle.
 * Inputs are private contiguous copies; the result owns a new immutable buffer.
 * No source freshness, evidence inventory or motion decision lives here. */
static PyObject *cell_distances(PyObject *self, PyObject *args) {
    PyObject *polygon, *cells, *result=NULL; Py_buffer p={0}, c={0};
    if(!PyArg_ParseTuple(args,"OO",&polygon,&cells))return NULL;
    if(PyObject_GetBuffer(polygon,&p,PyBUF_FORMAT|PyBUF_STRIDES)<0)return NULL;
    if(PyObject_GetBuffer(cells,&c,PyBUF_FORMAT|PyBUF_STRIDES)<0)goto done;
    if(!p.format||!c.format||p.suboffsets||c.suboffsets||
       !PyBuffer_IsContiguous(&p,'C')||!PyBuffer_IsContiguous(&c,'C')||
       p.ndim!=3||p.shape[1]!=4||p.shape[2]!=2||p.itemsize!=8||strcmp(p.format,"d")||
       c.ndim!=2||c.shape[0]!=p.shape[0]||c.shape[1]!=2||c.itemsize!=8||
       (strcmp(c.format,"q")&&strcmp(c.format,"l"))||p.shape[0]>PY_SSIZE_T_MAX/8) {
        PyErr_SetString(PyExc_TypeError,"cell_distance_buffer_contract");goto done;
    }
    Py_ssize_t n=p.shape[0];
    for(Py_ssize_t i=0;i<n;i++) {
        double vertices[8];memcpy(vertices,(char *)p.buf+i*64,64);
        for(int k=0;k<8;k++)if(!isfinite(vertices[k])) {
            PyErr_SetString(PyExc_ValueError,"cell_distance_nonfinite");goto done;
        }
        for(int k=0;k<4;k++) {
            double dx=vertices[2*((k+1)%4)]-vertices[2*k];
            double dy=vertices[2*((k+1)%4)+1]-vertices[2*k+1];
            if(!(dx*dx+dy*dy>0)||!isfinite(dx*dx+dy*dy)) {
                PyErr_SetString(PyExc_ValueError,"cell_distance_degenerate");goto done;
            }
        }
        for(int k=0;k<2;k++)if(center(&c,i,k)<-4503599627370496LL||center(&c,i,k)>4503599627370496LL) {
            PyErr_SetString(PyExc_ValueError,"cell_distance_coordinate_range");goto done;
        }
    }
    result=PyBytes_FromStringAndSize(NULL,n*8);if(!result)goto done;
    char *out=PyBytes_AS_STRING(result);
    Py_BEGIN_ALLOW_THREADS
    for(Py_ssize_t i=0;i<n;i++) {
        double rectangle[8];memcpy(rectangle,(char *)p.buf+i*64,64);
        double r=(double)center(&c,i,0),col=(double)center(&c,i,1);
        double square[8]={col,r,col+1,r,col+1,r+1,col,r+1};
        double best=INFINITY;
        for(int side=0;side<2;side++) {
            const double *points=side?square:rectangle,*edges=side?rectangle:square;
            for(int a=0;a<4;a++)for(int b=0;b<4;b++) {
                int next=(b+1)%4;
                double vx=edges[2*next]-edges[2*b],vy=edges[2*next+1]-edges[2*b+1];
                double dx=points[2*a]-edges[2*b],dy=points[2*a+1]-edges[2*b+1];
                double f=(dx*vx+dy*vy)/(vx*vx+vy*vy);
                if(f<0)f=0;
                if(f>1)f=1;
                double ex=dx-f*vx,ey=dy-f*vy,d=ex*ex+ey*ey;
                if(d<best)best=d;
            }
        }
        double distance=sqrt(best);memcpy(out+i*8,&distance,8);
    }
    Py_END_ALLOW_THREADS
 done:
    if(c.obj)PyBuffer_Release(&c);
    PyBuffer_Release(&p);return result;
}
static PyMethodDef methods[]={{"clear",clear,METH_VARARGS,"Reserved cell-centre sweep; no motion authority."},{"cell_distances",cell_distances,METH_VARARGS,"Exact rectangle/cell boundary distances; no evidence authority."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_reserved_sweep",NULL,-1,methods};
PyMODINIT_FUNC PyInit__reserved_sweep(void) {return PyModule_Create(&module);}
