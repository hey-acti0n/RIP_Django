import json
import os
import time
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests


AUTH_TOKEN = "secret123"  # 8 байт токен для псевдо-авторизации


USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"
PROTOCOL = "https" if USE_HTTPS else "http"
MAIN_SERVICE_URL = f"{PROTOCOL}://localhost:8080/api/v1"


def calculate_unit_cost(material):
   
    base_price = 100.0  # Базовая цена
    
    if material.get('density') is not None:
        base_price += material['density'] * 0.1
    
    if material.get('thickness') is not None:
        base_price += material['thickness'] * 2.0
    
    return base_price


def calculate_total_cost(calculation_id):
    
    delay = random.uniform(5, 10)
    time.sleep(delay)
    
    try:
        # Получаем данные расчета из Go API
        get_url = f"{MAIN_SERVICE_URL}/calculations/{calculation_id}"
        # Отключаем проверку SSL для HTTPS в разработке (самоподписанные сертификаты)
        # В production должно быть verify=True
        request_kwargs = {"timeout": 30}
        if USE_HTTPS:
            request_kwargs["verify"] = False  # Для разработки с самоподписанными сертификатами
        response = requests.get(get_url, **request_kwargs)
        
        if response.status_code != 200:
            print(f"Failed to get calculation {calculation_id}: {response.status_code} - {response.text}")
            # В случае ошибки отправляем 0
            total_cost = 0.0
            status = "failed"
        else:
            calculation_data = response.json()
            material_calculations = calculation_data.get('material_calculations', [])
            
            # Рассчитываем общую стоимость
            total_cost = 0.0
            
            for mc in material_calculations:
                material = mc.get('material', {})
                quantity = mc.get('quantity', 1)
                
                # Рассчитываем стоимость единицы материала
                unit_cost = calculate_unit_cost(material)
                
                # Рассчитываем стоимость для данного материала (unit_cost * quantity)
                material_total_cost = unit_cost * quantity
                
                # Добавляем к общей стоимости
                total_cost += material_total_cost
                
                print(f"Material {material.get('name', 'Unknown')}: unit_cost={unit_cost:.2f}, quantity={quantity}, total={material_total_cost:.2f}")
            
            print(f"Total cost for calculation {calculation_id}: {total_cost:.2f}")
            status = "success" if total_cost > 0 else "failed"
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting calculation data for {calculation_id}: {str(e)}")
        total_cost = 0.0
        status = "failed"
    except Exception as e:
        print(f"Unexpected error calculating cost for {calculation_id}: {str(e)}")
        total_cost = 0.0
        status = "failed"
    
    # Отправляем PUT запрос к основному сервису
    update_url = f"{MAIN_SERVICE_URL}/calculations/{calculation_id}/update-result"
    
    payload = {
        "total_cost": total_cost,
        "status": status
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": AUTH_TOKEN  # Псевдо-авторизация через токен
    }
    
    try:
        # Отключаем проверку SSL для HTTPS в разработке
        request_kwargs = {"json": payload, "headers": headers, "timeout": 30}
        if USE_HTTPS:
            request_kwargs["verify"] = False  # Для разработки с самоподписанными сертификатами
        response = requests.put(update_url, **request_kwargs)
        if response.status_code == 200:
            print(f"Successfully updated calculation {calculation_id} with total_cost={total_cost:.2f}")
        else:
            print(f"Failed to update calculation {calculation_id}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending PUT request for calculation {calculation_id}: {str(e)}")


@csrf_exempt
@require_http_methods(["POST"])
def calculate_cost(request):
    """
    POST endpoint для запуска асинхронного расчета стоимости.
    Принимает calculation_id в теле запроса.
    """
    try:
        data = json.loads(request.body)
        calculation_id = data.get('calculation_id') or data.get('pk')
        
        if not calculation_id:
            return JsonResponse({
                "error": "calculation_id or pk is required"
            }, status=400)
        
        # Запускаем расчет в отдельном потоке (асинхронно)
        thread = threading.Thread(
            target=calculate_total_cost,
            args=(calculation_id,)
        )
        thread.daemon = True
        thread.start()
        
        # Сразу возвращаем ответ, не дожидаясь завершения расчета
        return JsonResponse({
            "message": "Calculation initiated",
            "calculation_id": calculation_id,
            "status": "processing"
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)
