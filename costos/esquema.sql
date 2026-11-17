-- Esquema de la base de datos (SQLite).
-- Tres tablas: una obra tiene muchas partidas, y una partida tiene muchos gastos.

CREATE TABLE IF NOT EXISTS obras (
    id                 INTEGER PRIMARY KEY,
    codigo             TEXT NOT NULL UNIQUE,      -- identificador corto, ej. "OB-01"
    nombre             TEXT NOT NULL,
    cliente            TEXT,
    fecha_inicio       TEXT,                      -- SQLite guarda fechas como texto AAAA-MM-DD
    fecha_fin_prevista TEXT
);

-- Una partida es un renglón del presupuesto (ej. "Cimientos", "Techos").
CREATE TABLE IF NOT EXISTS partidas (
    id          INTEGER PRIMARY KEY,
    obra_id     INTEGER NOT NULL REFERENCES obras(id),
    nombre      TEXT NOT NULL,
    categoria   TEXT,
    presupuesto REAL NOT NULL CHECK (presupuesto >= 0),
    avance      REAL NOT NULL DEFAULT 0 CHECK (avance BETWEEN 0 AND 1),  -- 0.35 = 35 % construido
    UNIQUE (obra_id, nombre)                      -- no se repite una partida dentro de la misma obra
);

-- Cada gasto real (factura, planilla, etc.) se asigna a una partida.
CREATE TABLE IF NOT EXISTS gastos (
    id          INTEGER PRIMARY KEY,
    partida_id  INTEGER NOT NULL REFERENCES partidas(id),
    fecha       TEXT NOT NULL,
    proveedor   TEXT,
    documento   TEXT,
    descripcion TEXT,
    monto       REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gastos_partida ON gastos(partida_id);
