
VISUAL_TYPE_NONE                      = 0
VISUAL_TYPE_X11                       = 1
VISUAL_TYPE_AA                        = 2
VISUAL_TYPE_FB                        = 3
VISUAL_TYPE_GTK                       = 4
VISUAL_TYPE_DFB                       = 5
VISUAL_TYPE_PM                        = 6    # used by the OS/2 port
VISUAL_TYPE_DIRECTX                   = 7    # used by the win32/msvc port
VISUAL_TYPE_CACA                      = 8
VISUAL_TYPE_MACOSX                    = 9

MASTER_SLAVE_PLAY                     = (1<<0)
MASTER_SLAVE_STOP                     = (1<<1)
MASTER_SLAVE_SPEED                    = (1<<2)

TRICK_MODE_OFF                        = 0
TRICK_MODE_SEEK_TO_POSITION           = 1
TRICK_MODE_SEEK_TO_TIME               = 2
TRICK_MODE_FAST_FORWARD               = 3
TRICK_MODE_FAST_REWIND                = 4

ENGINE_PARAM_VERBOSITY                = 1

PARAM_SPEED                           = 1    # see below
PARAM_AV_OFFSET                       = 2    # unit: 1/90000 sec
PARAM_AUDIO_CHANNEL_LOGICAL           = 3    # -1 => auto, -2 => off
PARAM_SPU_CHANNEL                     = 4
PARAM_VIDEO_CHANNEL                   = 5
PARAM_AUDIO_VOLUME                    = 6    # 0..100
PARAM_AUDIO_MUTE                      = 7    # 1=>mute, 0=>unmute
PARAM_AUDIO_COMPR_LEVEL               = 8    # <100=>off, % compress otherw
PARAM_AUDIO_AMP_LEVEL                 = 9    # 0..200, 100=>100% (default)
PARAM_AUDIO_REPORT_LEVEL              = 10    # 1=>send events, 0=> don't
PARAM_VERBOSITY                       = 11    # control console output
PARAM_SPU_OFFSET                      = 12    # unit: 1/90000 sec
PARAM_IGNORE_VIDEO                    = 13    # disable video decoding
PARAM_IGNORE_AUDIO                    = 14    # disable audio decoding
PARAM_IGNORE_SPU                      = 15    # disable spu decoding
PARAM_BROADCASTER_PORT                = 16    # 0: disable, x: server port
PARAM_METRONOM_PREBUFFER              = 17    # unit: 1/90000 sec
PARAM_EQ_30HZ                         = 18    # equalizer gains -100..100
PARAM_EQ_60HZ                         = 19    # equalizer gains -100..100
PARAM_EQ_125HZ                        = 20    # equalizer gains -100..100
PARAM_EQ_250HZ                        = 21    # equalizer gains -100..100
PARAM_EQ_500HZ                        = 22    # equalizer gains -100..100
PARAM_EQ_1000HZ                       = 23    # equalizer gains -100..100
PARAM_EQ_2000HZ                       = 24    # equalizer gains -100..100
PARAM_EQ_4000HZ                       = 25    # equalizer gains -100..100
PARAM_EQ_8000HZ                       = 26    # equalizer gains -100..100
PARAM_EQ_16000HZ                      = 27    # equalizer gains -100..100
PARAM_AUDIO_CLOSE_DEVICE              = 28    # force closing audio device
PARAM_AUDIO_AMP_MUTE                  = 29    # 1=>mute, 0=>unmute
PARAM_FINE_SPEED                      = 30    # 1.000.000 => normal speed

SPEED_PAUSE                           = 0
SPEED_SLOW_4                          = 1
SPEED_SLOW_2                          = 2
SPEED_NORMAL                          = 4
SPEED_FAST_2                          = 8
SPEED_FAST_4                          = 16

FINE_SPEED_NORMAL                     = 1000000

PARAM_VO_DEINTERLACE                  = 0x01000000    # bool
PARAM_VO_ASPECT_RATIO                 = 0x01000001    # see below
PARAM_VO_HUE                          = 0x01000002    # 0..65535
PARAM_VO_SATURATION                   = 0x01000003    # 0..65535
PARAM_VO_CONTRAST                     = 0x01000004    # 0..65535
PARAM_VO_BRIGHTNESS                   = 0x01000005    # 0..65535
PARAM_VO_ZOOM_X                       = 0x01000008    # percent
PARAM_VO_ZOOM_Y                       = 0x0100000d    # percent
PARAM_VO_PAN_SCAN                     = 0x01000009    # bool
PARAM_VO_TVMODE                       = 0x0100000a    # ???
PARAM_VO_CROP_LEFT                    = 0x01000020    # crop frame pixels
PARAM_VO_CROP_RIGHT                   = 0x01000021    # crop frame pixels
PARAM_VO_CROP_TOP                     = 0x01000022    # crop frame pixels
PARAM_VO_CROP_BOTTOM                  = 0x01000023    # crop frame pixels

VO_ZOOM_STEP                          = 100
VO_ZOOM_MAX                           = 400
VO_ZOOM_MIN                           = -85
VO_ASPECT_AUTO                        = 0
VO_ASPECT_SQUARE                      = 1    # 1:1
VO_ASPECT_4_3                         = 2    # 4:3
VO_ASPECT_ANAMORPHIC                  = 3    # 16:9
VO_ASPECT_DVB                         = 4    # 2.11:1
VO_ASPECT_NUM_RATIOS                  = 5
VO_ASPECT_PAN_SCAN                    = 41
VO_ASPECT_DONT_TOUCH                  = 42

DEMUX_DEFAULT_STRATEGY                = 0
DEMUX_REVERT_STRATEGY                 = 1
DEMUX_CONTENT_STRATEGY                = 2
DEMUX_EXTENSION_STRATEGY              = 3

VERBOSITY_NONE                        = 0
VERBOSITY_LOG                         = 1
VERBOSITY_DEBUG                       = 2

IMGFMT_YV12                           = ((50<<24)|(49<<16)|(86<<8)|89)
IMGFMT_YUY2                           = ((50<<24)|(89<<16)|(85<<8)|89)
IMGFMT_XVMC                           = ((67<<24)|(77<<16)|(118<<8)|88)
IMGFMT_XXMC                           = ((67<<24)|(77<<16)|(120<<8)|88)

POST_TYPE_VIDEO_FILTER                = 0x010000
POST_TYPE_VIDEO_VISUALIZATION         = 0x010001
POST_TYPE_VIDEO_COMPOSE               = 0x010002
POST_TYPE_AUDIO_FILTER                = 0x020000
POST_TYPE_AUDIO_VISUALIZATION         = 0x020001
POST_DATA_VIDEO                       = 0
POST_DATA_AUDIO                       = 1
POST_DATA_INT                         = 3
POST_DATA_DOUBLE                      = 4
POST_DATA_PARAMETERS                  = 5

STATUS_IDLE                           = 0    # no mrl assigned
STATUS_STOP                           = 1
STATUS_PLAY                           = 2
STATUS_QUIT                           = 3

ERROR_NONE                            = 0
ERROR_NO_INPUT_PLUGIN                 = 1
ERROR_NO_DEMUX_PLUGIN                 = 2
ERROR_DEMUX_FAILED                    = 3
ERROR_MALFORMED_MRL                   = 4
ERROR_INPUT_FAILED                    = 5

LANG_MAX                              = 32

STREAM_INFO_BITRATE                   = 0
STREAM_INFO_SEEKABLE                  = 1
STREAM_INFO_VIDEO_WIDTH               = 2
STREAM_INFO_VIDEO_HEIGHT              = 3
STREAM_INFO_VIDEO_RATIO               = 4    # *10000
STREAM_INFO_VIDEO_CHANNELS            = 5
STREAM_INFO_VIDEO_STREAMS             = 6
STREAM_INFO_VIDEO_BITRATE             = 7
STREAM_INFO_VIDEO_FOURCC              = 8
STREAM_INFO_VIDEO_HANDLED             = 9     # codec available?
STREAM_INFO_FRAME_DURATION            = 10    # 1/90000 sec
STREAM_INFO_AUDIO_CHANNELS            = 11
STREAM_INFO_AUDIO_BITS                = 12
STREAM_INFO_AUDIO_SAMPLERATE          = 13
STREAM_INFO_AUDIO_BITRATE             = 14
STREAM_INFO_AUDIO_FOURCC              = 15
STREAM_INFO_AUDIO_HANDLED             = 16    # codec available?
STREAM_INFO_HAS_CHAPTERS              = 17
STREAM_INFO_HAS_VIDEO                 = 18
STREAM_INFO_HAS_AUDIO                 = 19
STREAM_INFO_IGNORE_VIDEO              = 20
STREAM_INFO_IGNORE_AUDIO              = 21
STREAM_INFO_IGNORE_SPU                = 22
STREAM_INFO_VIDEO_HAS_STILL           = 23
STREAM_INFO_MAX_AUDIO_CHANNEL         = 24
STREAM_INFO_MAX_SPU_CHANNEL           = 25
STREAM_INFO_AUDIO_MODE                = 26
STREAM_INFO_SKIPPED_FRAMES            = 27    # for 1000 frames delivered
STREAM_INFO_DISCARDED_FRAMES          = 28    # for 1000 frames delivered

META_INFO_TITLE                       = 0
META_INFO_COMMENT                     = 1
META_INFO_ARTIST                      = 2
META_INFO_GENRE                       = 3
META_INFO_ALBUM                       = 4
META_INFO_YEAR                        = 5
META_INFO_VIDEOCODEC                  = 6
META_INFO_AUDIOCODEC                  = 7
META_INFO_SYSTEMLAYER                 = 8
META_INFO_INPUT_PLUGIN                = 9
META_INFO_CDINDEX_DISCID              = 10
META_INFO_TRACK_NUMBER                = 11

MRL_TYPE_unknown                      = (0 << 0)
MRL_TYPE_dvd                          = (1 << 0)
MRL_TYPE_vcd                          = (1 << 1)
MRL_TYPE_net                          = (1 << 2)
MRL_TYPE_rtp                          = (1 << 3)
MRL_TYPE_stdin                        = (1 << 4)
MRL_TYPE_cda                          = (1 << 5)
MRL_TYPE_file                         = (1 << 6)
MRL_TYPE_file_fifo                    = (1 << 7)
MRL_TYPE_file_chardev                 = (1 << 8)
MRL_TYPE_file_directory               = (1 << 9)
MRL_TYPE_file_blockdev                = (1 << 10)
MRL_TYPE_file_normal                  = (1 << 11)
MRL_TYPE_file_symlink                 = (1 << 12)
MRL_TYPE_file_sock                    = (1 << 13)
MRL_TYPE_file_exec                    = (1 << 14)
MRL_TYPE_file_backup                  = (1 << 15)
MRL_TYPE_file_hidden                  = (1 << 16)

GUI_SEND_COMPLETION_EVENT             = 1    # DEPRECATED
GUI_SEND_DRAWABLE_CHANGED             = 2
GUI_SEND_EXPOSE_EVENT                 = 3
GUI_SEND_TRANSLATE_GUI_TO_VIDEO       = 4
GUI_SEND_VIDEOWIN_VISIBLE             = 5
GUI_SEND_SELECT_VISUAL                = 8
GUI_SEND_WILL_DESTROY_DRAWABLE        = 9

HEALTH_CHECK_OK                       = 0
HEALTH_CHECK_FAIL                     = 1
HEALTH_CHECK_UNSUPPORTED              = 2
HEALTH_CHECK_NO_SUCH_CHECK            = 3

CONFIG_TYPE_UNKNOWN                   = 0
CONFIG_TYPE_RANGE                     = 1
CONFIG_TYPE_STRING                    = 2
CONFIG_TYPE_ENUM                      = 3
CONFIG_TYPE_NUM                       = 4
CONFIG_TYPE_BOOL                      = 5

EVENT_UI_PLAYBACK_FINISHED            = 1    # frontend can e.g. move on to next playlist entry
EVENT_UI_CHANNELS_CHANGED             = 2    # inform ui that new channel info is available
EVENT_UI_SET_TITLE                    = 3    # request title display change in ui
EVENT_UI_MESSAGE                      = 4    # message (dialog) for the ui to display
EVENT_FRAME_FORMAT_CHANGE             = 5    # e.g. aspect ratio change during dvd playback
EVENT_AUDIO_LEVEL                     = 6    # report current audio level (l/r/mute)
EVENT_QUIT                            = 7    # last event sent when stream is disposed
EVENT_PROGRESS                        = 8    # index creation/network connections
EVENT_MRL_REFERENCE                   = 9    # demuxer->frontend: MRL reference(s) for the real stream
EVENT_UI_NUM_BUTTONS                  = 10    # number of buttons for interactive menus
EVENT_SPU_BUTTON                      = 11    # the mouse pointer enter/leave a button
EVENT_DROPPED_FRAMES                  = 12    # number of dropped frames is too high
EVENT_INPUT_MOUSE_BUTTON              = 101
EVENT_INPUT_MOUSE_MOVE                = 102
EVENT_INPUT_MENU1                     = 103
EVENT_INPUT_MENU2                     = 104
EVENT_INPUT_MENU3                     = 105
EVENT_INPUT_MENU4                     = 106
EVENT_INPUT_MENU5                     = 107
EVENT_INPUT_MENU6                     = 108
EVENT_INPUT_MENU7                     = 109
EVENT_INPUT_UP                        = 110
EVENT_INPUT_DOWN                      = 111
EVENT_INPUT_LEFT                      = 112
EVENT_INPUT_RIGHT                     = 113
EVENT_INPUT_SELECT                    = 114
EVENT_INPUT_NEXT                      = 115
EVENT_INPUT_PREVIOUS                  = 116
EVENT_INPUT_ANGLE_NEXT                = 117
EVENT_INPUT_ANGLE_PREVIOUS            = 118
EVENT_INPUT_BUTTON_FORCE              = 119
EVENT_INPUT_NUMBER_0                  = 120
EVENT_INPUT_NUMBER_1                  = 121
EVENT_INPUT_NUMBER_2                  = 122
EVENT_INPUT_NUMBER_3                  = 123
EVENT_INPUT_NUMBER_4                  = 124
EVENT_INPUT_NUMBER_5                  = 125
EVENT_INPUT_NUMBER_6                  = 126
EVENT_INPUT_NUMBER_7                  = 127
EVENT_INPUT_NUMBER_8                  = 128
EVENT_INPUT_NUMBER_9                  = 129
EVENT_INPUT_NUMBER_10_ADD             = 130
EVENT_SET_V4L2                        = 200
EVENT_PVR_SAVE                        = 201
EVENT_PVR_REPORT_NAME                 = 202
EVENT_PVR_REALTIME                    = 203
EVENT_PVR_PAUSE                       = 204
EVENT_SET_MPEG_DATA                   = 205
EVENT_VDR_RED                         = 300
EVENT_VDR_GREEN                       = 301
EVENT_VDR_YELLOW                      = 302
EVENT_VDR_BLUE                        = 303
EVENT_VDR_PLAY                        = 304
EVENT_VDR_PAUSE                       = 305
EVENT_VDR_STOP                        = 306
EVENT_VDR_RECORD                      = 307
EVENT_VDR_FASTFWD                     = 308
EVENT_VDR_FASTREW                     = 309
EVENT_VDR_POWER                       = 310
EVENT_VDR_CHANNELPLUS                 = 311
EVENT_VDR_CHANNELMINUS                = 312
EVENT_VDR_SCHEDULE                    = 313
EVENT_VDR_CHANNELS                    = 314
EVENT_VDR_TIMERS                      = 315
EVENT_VDR_RECORDINGS                  = 316
EVENT_VDR_SETUP                       = 317
EVENT_VDR_COMMANDS                    = 318
EVENT_VDR_BACK                        = 319
EVENT_VDR_USER1                       = 320
EVENT_VDR_USER2                       = 321
EVENT_VDR_USER3                       = 322
EVENT_VDR_USER4                       = 323
EVENT_VDR_USER5                       = 324
EVENT_VDR_USER6                       = 325
EVENT_VDR_USER7                       = 326
EVENT_VDR_USER8                       = 327
EVENT_VDR_USER9                       = 328
EVENT_VDR_VOLPLUS                     = 329
EVENT_VDR_VOLMINUS                    = 330
EVENT_VDR_MUTE                        = 331
EVENT_VDR_AUDIO                       = 332
EVENT_VDR_SETVIDEOWINDOW              = 350
EVENT_VDR_FRAMESIZECHANGED            = 351

MSG_NO_ERROR                          = 0     # (messages to UI)
MSG_GENERAL_WARNING                   = 1     # (warning message)
MSG_UNKNOWN_HOST                      = 2     # (host name)
MSG_UNKNOWN_DEVICE                    = 3     # (device name)
MSG_NETWORK_UNREACHABLE               = 4     # none
MSG_CONNECTION_REFUSED                = 5     # (host name)
MSG_FILE_NOT_FOUND                    = 6     # (file name or mrl)
MSG_READ_ERROR                        = 7     # (device/file/mrl)
MSG_LIBRARY_LOAD_ERROR                = 8     # (library/decoder)
MSG_ENCRYPTED_SOURCE                  = 9     # none
MSG_SECURITY                          = 10    # (security message)
MSG_AUDIO_OUT_UNAVAILABLE             = 11    # none
MSG_PERMISSION_ERROR                  = 12    # (file name or mrl)

TEXT_PALETTE_SIZE                     = 11

OSD_TEXT1                             = (0 * TEXT_PALETTE_SIZE)
OSD_TEXT2                             = (1 * TEXT_PALETTE_SIZE)
OSD_TEXT3                             = (2 * TEXT_PALETTE_SIZE)
OSD_TEXT4                             = (3 * TEXT_PALETTE_SIZE)
OSD_TEXT5                             = (4 * TEXT_PALETTE_SIZE)
OSD_TEXT6                             = (5 * TEXT_PALETTE_SIZE)
OSD_TEXT7                             = (6 * TEXT_PALETTE_SIZE)
OSD_TEXT8                             = (7 * TEXT_PALETTE_SIZE)
OSD_TEXT9                             = (8 * TEXT_PALETTE_SIZE)
OSD_TEXT10                            = (9 * TEXT_PALETTE_SIZE)

TEXTPALETTE_WHITE_BLACK_TRANSPARENT   = 0
TEXTPALETTE_WHITE_NONE_TRANSPARENT    = 1
TEXTPALETTE_WHITE_NONE_TRANSLUCID     = 2
TEXTPALETTE_YELLOW_BLACK_TRANSPARENT  = 3

OSD_CAP_FREETYPE2                     = 0x0001    # freetype2 support compiled in
OSD_CAP_UNSCALED                      = 0x0002    # unscaled overlays supp. by vo drv
