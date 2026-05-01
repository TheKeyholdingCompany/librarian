"""link seed book photos

Revision ID: b9c4d8e1a2f3
Revises: e7f3a2b91d4c
Create Date: 2026-05-01 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9c4d8e1a2f3'
down_revision = 'e7f3a2b91d4c'
branch_labels = None
depends_on = None


PHOTO_BY_BOOK_NAME = {
    "Coaching for Performance": "7afcce6baf3e410090917ca8cb56cdc4_coaching_for_performace.png",
    "Why We Sleep": "f985bd2240054d218384b9dea03bad00_Why_we_sleep.png",
    "Invisible Women": "d2b4e33e40aa4a38a54ab8a6efd00eb4_Invisible-Women-RBD.png",
    "The Humans": "a7434856541c40a9b1e278e34ae6ea10_the_humans.jpg",
    "Sapiens": "4d2d254cbc554c8ba9b7f89443270d89_Sapiens.jpg",
    "Measure What Matters": "52931d6b6e1a4f3e88258b3a9971c2e2_John-Doerr-Measure-What-Matters-OKRs-The-Simple-Idea-that-Drives-10x-Growth-670x1024.jpg",
    "Emotional Intelligence": "946362cb8b9f4f9d8eb85bac147d1af8_Emotional_Inteligence.png",
    "American Dirt": "9a833b4100d042fcb0f1546b36942301_american_dirt.png",
    "The Psychology Book": "a3022c997e294c46ad9cb6dca084fa05_phyc_book.png",
    "The Science of Living": "6955c7e6e66342b1a63fd177a5ef5c67_The_science_of_living.png",
    "The Chimp Paradox": "c32e7e8850be454e8eafa481b42e1a7a_chimp.png",
    "How We Rise": "c44ff271e7eb4feb8424e91637ec1e4b_Rise.png",
    "Becoming": "5d4a2e0c62b7439c84d55eb297e9e0a8_Becoming.png",
    "HR Transformation": "897ff6b6b14b4a1cb520c1f7a30cb05c_transformational_hr.png",
    "Now, Discover Your Strengths": "d18d611af55b45ffb7879999df9d9dad_NowDiscoverYourStrengths.png",
    "A Promised Land": "14b1a79b788446e7a1f92d96aa938497_Promised_land.png",
    "Scattered Minds": "c322c12fa1bc4d3ab75c5e52b323d0c3_Scattered_Minds.png",
    "Man’s Search for Meaning": "79dadba91c1e441f8fa867760c2688f6_mans_seaching_for_meaning.png",
    "Show Me the Numbers": "e814dc1f06234769a201f5403cde297c_Show_me_the_numbers.png",
    "Wasteland": "17128b355b264d0784ff7f51dca2ae63_Wasteland-673x1024.png",
    "How to Avoid a Climate Disaster": "e05a0b9cd98a44cdbd1a6503398d03c4_HowToAvoidAClimateDisaster.png",
    "How to Break Up with Your Phone": "cae6bb3a3ca44481bc1db3f1efe12ef5_HowToBreakUpWithYourPhone.png",
    "Life on Our Planet": "9f9cd01861e840769cbb88ca6899464c_ALiveOnOurPlanet.png",
}


def upgrade():
    conn = op.get_bind()
    stmt = sa.text("UPDATE books SET photo_filename = :filename WHERE name = :name")
    for name, filename in PHOTO_BY_BOOK_NAME.items():
        conn.execute(stmt, {"name": name, "filename": filename})


def downgrade():
    conn = op.get_bind()
    stmt = sa.text("UPDATE books SET photo_filename = NULL WHERE name = :name")
    for name in PHOTO_BY_BOOK_NAME:
        conn.execute(stmt, {"name": name})
