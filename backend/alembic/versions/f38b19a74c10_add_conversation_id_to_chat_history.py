"""add conversation_id to chat_history

Revision ID: f38b19a74c10
Revises: e72f629ad12e
Create Date: 2026-09-13 12:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f38b19a74c10'
down_revision: Union[str, Sequence[str], None] = 'e72f629ad12e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_history', sa.Column('conversation_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_chat_history_conversation_id'), 'chat_history', ['conversation_id'], unique=False)
    # Backfill any existing historical records so they belong to default conversation 1
    op.execute("UPDATE chat_history SET conversation_id = 1 WHERE conversation_id IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_chat_history_conversation_id'), table_name='chat_history')
    op.drop_column('chat_history', 'conversation_id')
