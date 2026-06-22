from fastapi import FastAPI
import base64
import uvicorn

app = FastAPI()

LINKS = [
    "vless://b7f5516d-3395-4aa2-8fda-b5a3bb470632@171.22.30.206:4758?type=tcp&encryption=none&security=reality&pbk=F5BaTYzHDdFwfzYafEa4dMgLbxJivoAJNMnPRh_xU28&fp=chrome&sni=www.sony.com&sid=cb4f664cf2ac&spx=%2F#Bot-Neth",
    "vless://d6094842-c883-4074-ba21-20b426b8725f@93.177.117.96:4758?type=tcp&encryption=none&security=reality&pbk=dn6I73qqO5RNkT9gFjZcM6Wnz1xw9SVcGEALbLOBSlk&fp=chrome&sni=www.sony.com&sid=94cabf&spx=%2F#Bot-t35vht26",
    "vless://c8184a73-2dd9-447b-ac8e-5423ad0072fb@138.124.96.235:4758?type=tcp&encryption=none&security=reality&pbk=Fs3nVjrYkTiPWOYsWlA_FlQk0baj4UwS4w_kWjyJvl4&fp=chrome&sni=www.apple.com&sid=423d8a4006&spx=%2F#Bot-egypt",
]

@app.get("/sub/test")
async def sub():
    from fastapi.responses import Response
    content = "\n".join(LINKS)
    encoded = base64.b64encode(content.encode()).decode()
    return Response(content=encoded, media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)