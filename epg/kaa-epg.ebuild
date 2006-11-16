# Copyright 2006 by Dirk Meyer
# Distributed under the terms of the GNU General Public License v2
#
# Since this module is not released yet, this ebuild only
# installs the dependencies and not the module itself.

# inherit eutils distutils

DESCRIPTION="Kaa EPG"
HOMEPAGE="http://www.freevo.org/kaa"
SRC_URI=""

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="~amd64 ~ia64 ~ppc ~sparc x86"

DEPEND="${DEPEND}
	dev-python/kaa-base
	dev-libs/libxml2
	>=dev-db/sqlite-3.3.6
	>=dev-python/pysqlite-2.3.1"

