#ifndef _EPEG_H
#define _EPEG_H

typedef enum _Epeg_Colorspace
    {
	EPEG_GRAY8,
	EPEG_YUV8,
	EPEG_RGB8,
	EPEG_BGR8,
	EPEG_RGBA8,
	EPEG_BGRA8,
	EPEG_ARGB32,
	EPEG_CMYK
    }
    Epeg_Colorspace;

typedef struct _Epeg_Image          Epeg_Image;
typedef struct _Epeg_Thumbnail_Info Epeg_Thumbnail_Info;

struct _Epeg_Thumbnail_Info
{
    char                   *uri;
    unsigned long long int  mtime;
    int                     w, h;
    char                   *mimetype;
};

Epeg_Image   *epeg_file_open                 (const char *file);
void          epeg_size_get                  (Epeg_Image *im, int *w, int *h);
void          epeg_decode_size_set           (Epeg_Image *im, int w, int h);
const void   *epeg_pixels_get                (Epeg_Image *im);
void          epeg_pixels_free               (Epeg_Image *im, const void *data);
void          epeg_close                     (Epeg_Image *im);

#endif
