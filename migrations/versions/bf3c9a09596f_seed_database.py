"""insert initial books"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = "bf3c9a09596f"
down_revision = "bf3c9a09596e"
branch_labels = None
depends_on = None


def upgrade():
    books_table = sa.table(
        "books",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)

    op.bulk_insert(
        books_table,
        [
            # Top Shelf
            {"name": "Coaching for Performance", "description": "John Whitmore", "created_at": now},
            {"name": "Why We Sleep", "description": "Matthew Walker", "created_at": now},
            {"name": "Invisible Women", "description": "Caroline Criado Perez", "created_at": now},
            {"name": "The Humans", "description": "Matt Haig", "created_at": now},
            {"name": "Lost at Sea", "description": "Jon Ronson", "created_at": now},
            {"name": "Sapiens", "description": "Yuval Noah Harari", "created_at": now},
            {"name": "Measure What Matters", "description": "John Doerr", "created_at": now},
            {"name": "Talk Like TED", "description": "Carmine Gallo", "created_at": now},
            {"name": "Emotional Intelligence", "description": "Daniel Goleman", "created_at": now},
            {"name": "Take Your Company Global", "description": "Nataly Kelly", "created_at": now},

            # Middle Shelf
            {"name": "American Dirt", "description": "Jeanine Cummins", "created_at": now},
            {"name": "Not the End of the World", "description": "Hannah Ritchie", "created_at": now},
            {"name": "The Psychology Book", "description": "DK", "created_at": now},
            {"name": "The Science of Living", "description": "DK", "created_at": now},
            {"name": "The Chimp Paradox", "description": "Steve Peters", "created_at": now},
            {"name": "Living Planet", "description": "David Attenborough", "created_at": now},
            {"name": "How We Rise", "description": "Michael Hyatt", "created_at": now},
            {"name": "Becoming", "description": "Michelle Obama", "created_at": now},
            {"name": "HR Transformation", "description": "Lucy Adams", "created_at": now},
            {"name": "Now, Discover Your Strengths", "description": "Marcus Buckingham & Donald O. Clifton", "created_at": now},
            {"name": "A Promised Land", "description": "Barack Obama", "created_at": now},
            {"name": "Factfulness", "description": "Hans Rosling", "created_at": now},
            {"name": "Scattered Minds", "description": "Gabor Maté", "created_at": now},
            {"name": "Invisible Women", "description": "Caroline Criado Perez", "created_at": now},
            {"name": "Man’s Search for Meaning", "description": "Viktor E. Frankl", "created_at": now},

            # Bottom Shelf
            {"name": "Show Me the Numbers", "description": "Stephen Few", "created_at": now},
            {"name": "Building Microservices", "description": "Sam Newman", "created_at": now},
            {"name": "Wasteland", "description": "Oliver Franklin-Wallis", "created_at": now},
            {"name": "How to Avoid a Climate Disaster", "description": "Bill Gates", "created_at": now},
            {"name": "How to Break Up with Your Phone", "description": "Catherine Price", "created_at": now},
            {"name": "The Blue Zones", "description": "Dan Buettner", "created_at": now},
            {"name": "Life on Our Planet", "description": "David Attenborough", "created_at": now},
        ],
    )


def downgrade():
    # Remove all inserted books by name
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM books
            WHERE name IN (
                'Coaching for Performance',
                'Why We Sleep',
                'Invisible Women',
                'The Humans',
                'Lost at Sea',
                'Sapiens',
                'Measure What Matters',
                'Talk Like TED',
                'Emotional Intelligence',
                'Take Your Company Global',
                'American Dirt',
                'Not the End of the World',
                'The Psychology Book',
                'The Science of Living',
                'The Chimp Paradox',
                'Living Planet',
                'How We Rise',
                'Becoming',
                'HR Transformation',
                'Now, Discover Your Strengths',
                'A Promised Land',
                'Factfulness',
                'Scattered Minds',
                'Man’s Search for Meaning',
                'Show Me the Numbers',
                'Building Microservices',
                'Wasteland',
                'How to Avoid a Climate Disaster',
                'How to Break Up with Your Phone',
                'The Blue Zones',
                'Life on Our Planet'
            )
            """
        )
    )