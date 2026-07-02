"""Cross-dialect column types.

On PostgreSQL these render as native ARRAY columns (per spec §7.3);
on SQLite (tests) they fall back to JSON. Behavior is identical for
whole-value reads/writes, which is all we do with these columns.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

IntList = sa.JSON().with_variant(postgresql.ARRAY(sa.Integer()), "postgresql")
StrList = sa.JSON().with_variant(postgresql.ARRAY(sa.Text()), "postgresql")
