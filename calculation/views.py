import json
import random
import time
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests


# Константа для токена авторизации (8 байт)
AUTH_TOKEN = "secret123"  # 8 байт токен для псевдо-авторизации

# URL основного Go сервиса
MAIN_SERVICE_URL = "http://localhost:8080/api/v1"


def calculate_total_cost(calculation_id):
    """
    Выполняет расчет total_cost с задержкой 5-10 секунд.
    Генерирует случайный результат (успех/неуспех).
    """
    # Задержка от 5 до 10 секунд
    delay = random.uniform(5, 10)
    time.sleep(delay)
    
    # Генерируем случайный результат (успех/неуспех)
    # В случае успеха - случайная стоимость от 1000 до 10000
    # В случае неуспеха - 0 или отрицательное значение
    is_success = random.choice([True, False])
    
   
def calculate_unit_cost(material):
   
    base_price = 100.0  # Базовая цена
    
    if material.get('density') is not None:
        base_price += material['density'] * 0.1
    
    if material.get('thickness') is not None:
        base_price += material['thickness'] * 2.0
    
    return base_price
    
    # Отправляем PUT запрос к основному сервису
    update_url = f"{MAIN_SERVICE_URL}/calculations/{calculation_id}/update-result"
    
    payload = {
        "total_cost": total_cost,
        "status": "success" if is_success else "failed"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": AUTH_TOKEN  # Псевдо-авторизация через токен
    }
    
    try:
        response = requests.put(update_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"Successfully updated calculation {calculation_id} with total_cost={total_cost}")
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
