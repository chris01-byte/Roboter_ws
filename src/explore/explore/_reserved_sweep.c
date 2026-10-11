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
/* Sutherland-Hodgman clipping in the identical four-plane/vertex order.
 * Areas remain calculated by the original NumPy reduction, including its
 * floating-point summation order. Zero-area contacts retain their vertices. */
static PyObject *cell_intersections(PyObject *self, PyObject *args) {
    PyObject *polygon,*cells,*vertices=NULL,*counts=NULL,*result=NULL;
    Py_buffer p={0},c={0};int overflow=0;
    if(!PyArg_ParseTuple(args,"OO",&polygon,&cells))return NULL;
    if(PyObject_GetBuffer(polygon,&p,PyBUF_FORMAT|PyBUF_STRIDES)<0)return NULL;
    if(PyObject_GetBuffer(cells,&c,PyBUF_FORMAT|PyBUF_STRIDES)<0)goto done;
    if(!p.format||!c.format||p.suboffsets||c.suboffsets||
       !PyBuffer_IsContiguous(&p,'C')||!PyBuffer_IsContiguous(&c,'C')||
       p.ndim!=3||p.shape[1]!=4||p.shape[2]!=2||p.itemsize!=8||strcmp(p.format,"d")||
       c.ndim!=2||c.shape[0]!=p.shape[0]||c.shape[1]!=2||c.itemsize!=8||
       (strcmp(c.format,"q")&&strcmp(c.format,"l"))||p.shape[0]>PY_SSIZE_T_MAX/192) {
        PyErr_SetString(PyExc_TypeError,"cell_clip_buffer_contract");goto done;
    }
    Py_ssize_t n=p.shape[0];
    for(Py_ssize_t i=0;i<n;i++) {
        double v[8];memcpy(v,(char *)p.buf+i*64,64);
        for(int k=0;k<8;k++)if(!isfinite(v[k])||fabs(v[k])>4503599627370496.) {
            PyErr_SetString(PyExc_ValueError,"cell_clip_coordinate_range");goto done;
        }
        for(int k=0;k<2;k++)if(center(&c,i,k)<-4503599627370496LL||center(&c,i,k)>4503599627370496LL) {
            PyErr_SetString(PyExc_ValueError,"cell_clip_coordinate_range");goto done;
        }
    }
    vertices=PyBytes_FromStringAndSize(NULL,n*192);
    counts=PyBytes_FromStringAndSize(NULL,n*8);
    if(!vertices||!counts)goto done;
    char *out=PyBytes_AS_STRING(vertices),*sizes=PyBytes_AS_STRING(counts);
    memset(out,0,n*192);
    Py_BEGIN_ALLOW_THREADS
    for(Py_ssize_t i=0;i<n&&!overflow;i++) {
        double current[12][2],next[12][2];int count=4;
        memcpy(current,(char *)p.buf+i*64,64);
        for(int plane=0;plane<4&&count;plane++) {
            int axis=plane/2,sign=plane%2?-1:1,kept=0;
            double bound=(double)(center(&c,i,1-axis)+plane%2);
            for(int j=0;j<count;j++) {
                const double *v=current[j],*prev=current[j?j-1:count-1];
                int inside=sign*(v[axis]-bound)>=0,before=sign*(prev[axis]-bound)>=0;
                if(inside!=before) {
                    if(kept>=12){overflow=1;break;}
                    double f=(bound-prev[axis])/(v[axis]-prev[axis]);
                    for(int k=0;k<2;k++)next[kept][k]=prev[k]+f*(v[k]-prev[k]);
                    kept++;
                }
                if(inside) {
                    if(kept>=12){overflow=1;break;}
                    memcpy(next[kept++],v,16);
                }
            }
            if(overflow)break;
            count=kept;memcpy(current,next,count*16);
        }
        if(!overflow) {
            memcpy(out+i*192,current,count*16);
            int64_t length=count;memcpy(sizes+i*8,&length,8);
        }
    }
    Py_END_ALLOW_THREADS
    if(overflow) {PyErr_SetString(PyExc_ValueError,"cell_clip_vertex_capacity");goto done;}
    result=PyTuple_Pack(2,vertices,counts);
 done:
    Py_XDECREF(vertices);Py_XDECREF(counts);
    if(c.obj)PyBuffer_Release(&c);
    PyBuffer_Release(&p);return result;
}
/* Backtrack the original distance field: identical strict descent, blocked
 * corners and (score,row,column) tie order. Keep the GIL while reading caller
 * buffers; this short arithmetic helper owns no source or movement decision. */
static int allowed_cell(const Py_buffer *b, Py_ssize_t r, Py_ssize_t c) {
    return *((unsigned char *)b->buf+r*b->strides[0]+c*b->strides[1]) != 0;
}
static PyObject *descending_route(PyObject *self, PyObject *args) {
    PyObject *mask,*distances,*route=NULL,*result=NULL;
    Py_buffer m={0},d={0};Py_ssize_t sr,sc,tr,tc;double axial,diagonal;
    if(!PyArg_ParseTuple(args,"OOnnnndd",&mask,&distances,&sr,&sc,&tr,&tc,
                         &axial,&diagonal))return NULL;
    if(PyObject_GetBuffer(mask,&m,PyBUF_FORMAT|PyBUF_STRIDES)<0)return NULL;
    if(PyObject_GetBuffer(distances,&d,PyBUF_FORMAT|PyBUF_STRIDES)<0)goto done;
    if(!m.format||!d.format||m.suboffsets||d.suboffsets||m.ndim!=2||d.ndim!=2||
       m.itemsize!=1||strcmp(m.format,"?")||d.itemsize!=8||strcmp(d.format,"d")||
       m.shape[0]!=d.shape[0]||m.shape[1]!=d.shape[1]) {
        PyErr_SetString(PyExc_TypeError,"descending_route_buffer_contract");goto done;
    }
    if(axial!=hypot(1.,0.)||diagonal!=hypot(1.,1.)) {
        PyErr_SetString(PyExc_ValueError,"descending_route_step_contract");goto done;
    }
    Py_ssize_t h=m.shape[0],w=m.shape[1];
    if(h<=0||w<=0||sr<0||sc<0||tr<0||tc<0||sr>=h||sc>=w||tr>=h||tc>=w||
       !allowed_cell(&m,sr,sc)||!allowed_cell(&m,tr,tc)||!isfinite(value(&d,tr,tc))) {
        result=Py_NewRef(Py_None);goto done;
    }
    if(h>PY_SSIZE_T_MAX/w) {
        PyErr_SetString(PyExc_ValueError,"descending_route_size_overflow");goto done;
    }
    route=PyList_New(0);if(!route)goto done;
    Py_ssize_t r=tr,c=tc,steps=0;
    for(;;) {
        if(steps++>=h*w) {result=Py_NewRef(Py_None);goto done;}
        PyObject *cell=Py_BuildValue("(nn)",r,c);if(!cell)goto done;
        int appended=PyList_Append(route,cell);Py_DECREF(cell);if(appended<0)goto done;
        if(r==sr&&c==sc)break;
        int found=0;double best=0.;Py_ssize_t br=0,bc=0;
        double current=value(&d,r,c);
        for(int dr=-1;dr<=1;dr++)for(int dc=-1;dc<=1;dc++) {
            Py_ssize_t nr=r+dr,nc=c+dc;
            if(!(dr||dc)||nr<0||nc<0||nr>=h||nc>=w||!allowed_cell(&m,nr,nc))continue;
            if(dr&&dc&&(!allowed_cell(&m,r,nc)||!allowed_cell(&m,nr,c)))continue;
            double next=value(&d,nr,nc);if(!(next<current-1e-9))continue;
            double score=next+(dr&&dc?diagonal:axial);
            if(!found||score<best||(score==best&&(nr<br||(nr==br&&nc<bc)))) {
                found=1;best=score;br=nr;bc=nc;
            }
        }
        if(!found) {result=Py_NewRef(Py_None);goto done;}
        r=br;c=bc;
    }
    if(PyList_Reverse(route)<0)goto done;
    result=PyList_AsTuple(route);
done:
    Py_XDECREF(route);
    if(d.obj)PyBuffer_Release(&d);
    PyBuffer_Release(&m);return result;
}
static PyMethodDef methods[]={{"clear",clear,METH_VARARGS,"Reserved cell-centre sweep; no motion authority."},{"cell_distances",cell_distances,METH_VARARGS,"Exact rectangle/cell boundary distances; no evidence authority."},{"cell_intersections",cell_intersections,METH_VARARGS,"Exact cell clipping; no evidence authority."},{"descending_route",descending_route,METH_VARARGS,"Original distance-field descent; no motion authority."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_reserved_sweep",NULL,-1,methods};
PyMODINIT_FUNC PyInit__reserved_sweep(void) {return PyModule_Create(&module);}
