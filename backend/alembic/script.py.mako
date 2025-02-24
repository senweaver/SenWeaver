"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import sqlalchemy_utils
from sqlalchemy_utils import ChoiceType
from senweaver.db.models.sqltypes import TextChoicesType,IntegerChoicesType
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}
<%
import re
import configparser
config = configparser.ConfigParser()
config.read('alembic.ini') 
remove_foreign_keys = config.get('alembic', 'remove_foreign_keys', fallback='false').lower() == 'true'
def replace_in_upgrades(upgrades): 
    if remove_foreign_keys:       
        pattern = r'sa\.ForeignKeyConstraint\([^)]*\),?(\s*)'
        if not upgrades:
            return "pass"
        upgrades = re.sub(pattern, '', upgrades, flags=re.DOTALL) 
    replacements = {
        'senweaver.db.models.sqltypes.': '', 
    }
    if not upgrades:
        return "pass"
    for old, new in replacements.items():
        upgrades = upgrades.replace(old, new)
    return upgrades
replaced_upgrades = replace_in_upgrades(upgrades)
%>
def upgrade() -> None:          
    ${replace_in_upgrades(upgrades)}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
