import fastapi
from typing import Optional
from fastapi import HTTPException, Depends, status
import sqlite3
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import hashlib
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = fastapi.FastAPI()
security_bearer = HTTPBearer()

origins = [
    "http://127.0.0.1:5000",
    "https://contactos-frond-5ed01e72bbb6.herokuapp.com"
]

# Configurar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Usuario(BaseModel):
    username: str
    password: str
    token: Optional[str] = None

class Contacto(BaseModel):
    email: str
    nombre: str
    telefono: str

def generate_token(data: str) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data.encode('utf-8'))
    return sha256_hash.hexdigest()

def get_conn():
    return sqlite3.connect("sql/contactos.db")

def token_valido(token: str, conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('SELECT username FROM usuarios WHERE token = ?', (token,))
    result = c.fetchone()
    return result is not None

def obtener_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        token = credentials.credentials
        if not token_valido(token, conn):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token
    finally:
        conn.close()

@app.get("/validate-token")
async def validate_token(token: str = Depends(obtener_token)):
    return {"mensaje": "Token válido"}


@app.get("/contactos", dependencies=[Depends(security_bearer)])
async def obtener_contactos(token: str = Depends(obtener_token)):
    conn = get_conn()  # Obtener la conexión a la base de datos
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM contactos')
        response = [{"email": row[0], "nombre": row[1], "telefono": row[2]} for row in c]
        return response
    finally:
        conn.close() 

@app.post("/contactos", dependencies=[Depends(security_bearer)])
async def crear_contacto(contacto: Contacto, token: str = Depends(obtener_token)):
    conn = get_conn()  # Obtener la conexión a la base de datos
    try:
        c = conn.cursor()
        c.execute('INSERT INTO contactos (email, nombre, telefono) VALUES (?, ?, ?)',
                  (contacto.email, contacto.nombre, contacto.telefono))
        conn.commit()
        return {"message": "Contacto guardado"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error al ingresar el contacto: {e}")
    finally:
        conn.close()  # Asegúrate de cerrar la conexión después de usarla



@app.get("/contactos/{email}", dependencies=[Depends(security_bearer)])
async def obtener_contacto(email: str,token: str = Depends(obtener_token)):
    c = get_conn.cursor()
    c.execute('SELECT * FROM contactos WHERE email = ?', (email,))
    contacto = None
    for row in c:
        contacto = {"email": row[0], "nombre": row[1], "telefono": row[2]}
    return contacto


@app.put("/contactos/{email}", dependencies=[Depends(security_bearer)])
async def actualizar_contacto(email: str, contacto: Contacto,token: str = Depends(obtener_token)):
    c = get_conn.cursor()
    c.execute('UPDATE contactos SET nombre = ?, telefono = ? WHERE email = ?',
              (contacto.nombre, contacto.telefono, email))
    get_conn.commit()
    return contacto


@app.delete("/contactos/{email}", dependencies=[Depends(security_bearer)])
async def eliminar_contacto(email: str,token: str = Depends(obtener_token)):
    c = get_conn.cursor()
    c.execute('DELETE FROM contactos WHERE email = ?', (email,))
    get_conn.commit()
    return {"mensaje": "Contacto eliminado"}


@app.post("/usuarios", response_model=dict)
async def crear_usuario(usuario: Usuario):
    conn = get_conn()
    try:
        # Hash de la contraseña (deberías usar un método más seguro en producción)
        hashed_password = hashlib.sha256(usuario.password.encode('utf-8')).hexdigest()

        # Generar token a partir de la contraseña
        usuario.token = generate_token(usuario.password)

        # Insertar el Usuario en la base de datos
        conn.execute('INSERT INTO usuarios (username, password, token) VALUES (?, ?, ?)',
                     (usuario.username, hashed_password, usuario.token))
        conn.commit()

        return {"message": "Usuario guardado", "tu token es": usuario.token}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error al ingresar el Usuario: {e}")
    finally:
        conn.close()


@app.get("/usuarios")
async def obtener_token(username: str, password: str):
    conn = get_conn()
    try:
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        c = conn.cursor()
        c.execute('SELECT token FROM usuarios WHERE username = ? AND password = ?', (username, hashed_password,))
        result = c.fetchone()

        if result:
            usuario = {"username": username, "password": hashed_password, "token": result[0]}
            return usuario
        else:
            return {"mensaje": "Credenciales inválidas"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el token: {e}")
    finally:
        conn.close()
