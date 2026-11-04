from typing import Optional
from sqlmodel import Session, select

from app.models.categoria import Categoria

class CategoriaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, categoria_id: int) -> Optional[Categoria]:
        return self.session.get(Categoria, categoria_id)

    def get_by_nombre(self, nombre: str) -> Optional[Categoria]:
        statement = select(Categoria).where(Categoria.nombre == nombre)
        return self.session.exec(statement).first()

    def list_paginado(self, offset: int = 0, limit: int = 20) -> list[Categoria]:
        statement = select(Categoria).offset(offset).limit(limit)
        return list(self.session.exec(statement).all())

    def crear(self, categoria: Categoria) -> Categoria:
        self.session.add(categoria)
        self.session.commit()
        self.session.refresh(categoria)
        return categoria

    def editar(self, categoria: Categoria) -> Categoria:
        self.session.add(categoria)
        self.session.commit()
        self.session.refresh(categoria)
        return categoria

    def borrar(self, categoria: Categoria) -> None:
        self.session.delete(categoria)
        self.session.commit()
