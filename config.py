import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'manufacturing-platform-secret-2024')
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
    UPLOAD_FOLDER = DATA_DIR
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    BATCH_PRODUCTION_FILE = os.path.join(DATA_DIR, 'batch_production_data.xlsx')
    BATCH_PROCESS_FILE = os.path.join(DATA_DIR, 'batch_process_data.xlsx')

    SPEC_LIMITS = {
        'Hardness': (50, 130),
        'Friability': (None, 1.0),
        'Dissolution_Rate': (80, None),
        'Content_Uniformity': (95, 105),
        'Moisture_Content': (None, 3.0),
    }

    PHASE_ENERGY_SHARE = {
        'Compression': 50.4,
        'Drying': 13.1,
        'Milling': 11.7,
        'Coating': 8.8,
        'Blending': 6.0,
        'Granulation': 4.9,
        'Quality_Testing': 3.8,
        'Preparation': 1.2
    }

    FAILING_BATCHES = [
        'T005','T008','T014','T018','T020','T025','T029','T031',
        'T034','T036','T040','T042','T045','T049','T051','T054','T056','T060'
    ]
    GOLDEN_BATCH = 'T059'
    WORST_BATCH = 'T056'
    ENERGY_RANGE = (21.4, 46.1)
    CO2_RANGE = (17.6, 37.8)