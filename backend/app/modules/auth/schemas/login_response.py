from pydantic import BaseModel


class LoginUser(BaseModel):
    ma_nguoi_dung: int
    ho_ten: str
    email: str
    vai_tro: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginUser