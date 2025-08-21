from fastapi.middleware.cors import CORSMiddleware

def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Or specify your frontend origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
