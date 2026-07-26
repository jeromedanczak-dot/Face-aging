from pydantic import BaseModel


class GeneratedImage(BaseModel):
    age: int
    url: str
    filename: str


class GenerationResponse(BaseModel):
    source_age: int
    ages: list[int]
    images: list[GeneratedImage]
    zip_url: str
