from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.knowledge_base.chunking import TextChunk
from app.models import KnowledgeDocument, User


class FailingEmbedding:
    def encode(self, texts):
        raise RuntimeError("embedding service unavailable")


def test_store_returns_tenant_scoped_lexical_hit_when_embedding_fails():
    from app.knowledge_base.supabase_store import SupabaseRAGStore

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add_all([User(id=1, username="owner", hashed_password="x"), User(id=2, username="other", hashed_password="x")])
    session.flush()
    session.add_all([
        KnowledgeDocument(id=4, user_id=1, course="Python", original_filename="variables.pdf", storage_name="owner.pdf", mime="application/pdf", size=3),
        KnowledgeDocument(id=5, user_id=2, course="Python", original_filename="private.pdf", storage_name="other.pdf", mime="application/pdf", size=3),
    ])
    session.commit()
    session.close()
    store = SupabaseRAGStore(Session, FailingEmbedding())

    store.index_document(1, 4, "Python", "variables.pdf", [
        TextChunk("Python variable types", "text", char_start=0, char_end=21),
    ])
    store.index_document(2, 5, "Python", "private.pdf", [
        TextChunk("Python variable private", "text", char_start=0, char_end=23),
    ])

    hits = store.search("Python variable", 1, "Python")

    assert [hit["citation_id"] for hit in hits] == ["4:0"]
    assert hits[0]["similarity"] > 0
