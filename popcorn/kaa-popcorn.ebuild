# Copyright 2006 by Dirk Meyer
# Distributed under the terms of the GNU General Public License v2
#
# Since this module is not released yet, this ebuild only
# installs the dependencies and not the module itself.

# inherit eutils distutils

DESCRIPTION="Kaa based media player API"
HOMEPAGE="http://www.freevo.org/kaa"
SRC_URI=""

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc x86"
IUSE="mplayer gstreamer xine libvisual dvd"

DEPEND="${DEPEND}
	dev-python/kaa-base
	dev-python/kaa-metadata
	dev-python/kaa-display
	mplayer? =media-video/mplayer-1.0_rc1
	gstreamer? ( 
	    >=dev-python/gst-python-0.10.1
		>=media-libs/gst-plugins-good-0.10.3
		>=media-libs/gst-plugins-bad-0.10.3
		>=media-libs/gst-plugins-ugly-0.10.3
		>=media-plugins/gst-plugins-a52dec-0.10.3
		>=media-plugins/gst-plugins-ffmpeg-0.10.1
		>=media-plugins/gst-plugins-mad-0.10.3
		dvd? >=media-plugins/gst-plugins-dvdread-0.10.4
		libvisual? >=media-plugins/gst-plugins-libvisual-0.10.4
		media-plugins/gst-plugins-theora
		media-plugins/gst-plugins-pango
		media-plugins/gst-plugins-vorbis
		media-plugins/gst-plugins-mpeg2dec
		media-plugins/gst-plugins-ogg
	)
	xine? dev-python/kaa-xine
	libvisual? >=media-libs/libvisual-0.2.0"
