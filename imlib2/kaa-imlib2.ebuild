# Copyright 2006 by Dirk Meyer
# Distributed under the terms of the GNU General Public License v2
#
# Since this module is not released yet, this ebuild only
# installs the dependencies and not the module itself.

# inherit eutils distutils

DESCRIPTION="Kaa Imlib2"
HOMEPAGE="http://www.freevo.org/kaa"
SRC_URI=""

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc x86"
IUSE="X"

DEPEND="${DEPEND}
	dev-python/kaa-base
	>=media-libs/imlib2-1.1.1
        X? virtual/x11"

