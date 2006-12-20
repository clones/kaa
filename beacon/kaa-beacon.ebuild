# Copyright 2006 by Dirk Meyer
# Distributed under the terms of the GNU General Public License v2
#
# Since this module is not released yet, this ebuild only
# installs the dependencies and not the module itself.

# inherit eutils distutils

DESCRIPTION="Kaa Beacon"
HOMEPAGE="http://www.freevo.org/kaa"
SRC_URI=""

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc x86"
IUSE="hal"

DEPEND="${DEPEND}
	dev-python/kaa-base
	dev-python/kaa-metadata
	dev-python/kaa-imlib2
	hal? ( 
	    sys-apps/dbus
		sys-apps/hal
		sys-apps/pmount
	)
	>=dev-db/sqlite-3.3.6
	>=dev-python/pysqlite-2.3.1
	>=media-libs/libpng-1.2.0
	>=media-libs/epeg-0.9.0.007"
