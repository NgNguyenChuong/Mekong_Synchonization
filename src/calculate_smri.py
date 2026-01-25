import pickle
import pandas as pd
import numpy as np

def calculate_smri(new_data):
    """
    Tính SMRI cho dữ liệu mới
    
    Parameters:
    -----------
    new_data : dict
        {'temp_c': value, 'solar': value, 
         'rain_mm': value, 'rh_percent': value, 'dem_mean': value,
            'temp_max_c': value, 'caibe_zos': value, 'cailon_zos': value,
            'cuadai_zos': value, 'cuatieu_zos': value, 'dinhan_zos': value,
            'ganhhao_zos': value, 'trande_zos': value, 'chau_doc_value': value, 'tan_chau_value': value}
    
    Returns:
    --------
    dict: {'SMRI_raw': float, 'SMRI_norm': float, 'Risk_Level': str}
    """
    # Load parameters
    with open('smri_scalers.pkl', 'rb') as f:
        scalers = pickle.load(f)
    with open('smri_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('smri_thresholds.pkl', 'rb') as f:
        thresh = pickle.load(f)
    
    # Normalize
    X_new = pd.DataFrame({
        'Nhiệt_độ': scalers['temp'].transform([[new_data['temp_c']]])[0][0],
        'Bức_xạ': scalers['solar'].transform([[new_data['solar']]])[0][0],
        'Mưa': scalers['rain'].transform([[new_data['rain_mm']]])[0][0],
        'Độ_ẩm': scalers['rh'].transform([[new_data['rh_percent']]])[0][0],
        'Cao_độ': scalers['dem'].transform([[new_data['dem_mean']]])[0][0],
        'Nhiệt_độ_max': scalers['temp_max'].transform([[new_data['temp_max_c']]])[0][0],
        'Caibe': scalers['caibe'].transform([[new_data['caibe_zos']]])[0][0],
        'Cailon': scalers['cailon'].transform([[new_data['cailon_zos']]])[0][0],
        'Cuadai': scalers['cuadai'].transform([[new_data['cuadai_zos']]])[0][0],
        'Cuatieu': scalers['cuatieu'].transform([[new_data['cuatieu_zos']]])[0][0],
        'Dinhan': scalers['dinhan'].transform([[new_data['dinhan_zos']]])[0][0],
        'Ganhhao': scalers['ganhhao'].transform([[new_data['ganhhao_zos']]])[0][0],
        'Trande': scalers['trande'].transform([[new_data['trande_zos']]])[0][0],
        'Chau_doc': scalers['chau_doc'].transform([[new_data['chau_doc_value']]])[0][0],
        'Tan_chau': scalers['tan_chau'].transform([[new_data['tan_chau_value']]])[0][0],
    }, index=[0])
    
    # Calculate SMRI
    smri_raw = model.predict(X_new)[0]
    smri_norm = (smri_raw - thresh['smri_min']) / (thresh['smri_max'] - thresh['smri_min'])
    smri_norm = np.clip(smri_norm, 0, 1)
    
    # Classify
    if smri_norm < thresh['low_threshold']:
        risk = 'Thấp'
    elif smri_norm < thresh['high_threshold']:
        risk = 'Trung bình'
    else:
        risk = 'Cao'
    
    return {
        'SMRI_raw': smri_raw,
        'SMRI_norm': smri_norm,
        'Risk_Level': risk
    }

# Ví dụ sử dụng:
if __name__ == "__main__":
    example_data = {
        'temp_dry_mean_dry': 32.5,
        'solar_sum_mua_kho': 250,
        'rain_dry_sum': 10,
        'mua_kho': 65,
        'dem_mean': 15
    }
    result = calculate_smri(example_data)
    print(f"SMRI = {result['SMRI_norm']:.4f} → Nguy cơ: {result['Risk_Level']}")
