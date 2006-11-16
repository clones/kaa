# Copyright 2006 by Dirk Meyer
# Distributed under the terms of the GNU General Public License v2
#
# Since this module is not released yet, this ebuild only
# installs the dependencies and not the module itself.

# inherit eutils distutils

DESCRIPTION="Kaa Display"
HOMEPAGE="http://www.freevo.org/kaa"
SRC_URI=""

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc x86"
IUSE="X directfb sdl evas"

DEPEND="${DEPEND}
	dev-python/kaa-base
	>=media-libs/imlib2-1.1.1
        X? virtual/x11
	directfb? dev-libs/DirectFB
	sdl? dev-python/pygame
	evas? >=x11-libs/evas-0.9.9.030"
