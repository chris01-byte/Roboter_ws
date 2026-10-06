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
static PyMethodDef methods[]={{"clear",clear,METH_VARARGS,"Reserved cell-centre sweep; no motion authority."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_reserved_sweep",NULL,-1,methods};
PyMODINIT_FUNC PyInit__reserved_sweep(void) {return PyModule_Create(&module);}
