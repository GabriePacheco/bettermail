import base64
import json
from urllib import error, request

from fastapi import HTTPException, status

from app.config import get_settings


PAYPHONE_CONFIRM_URL = "https://paymentbox.payphonetodoesposible.com/api/confirm"
PAYPHONE_TOKEN_CHARGE_URL = "https://pay.payphonetodoesposible.com/api/transaction/web"


def _settings():
    return get_settings()


def is_payphone_configured():
    settings = _settings()
    return settings.payphone_enabled and bool(settings.payphone_token.strip())


def amount_to_cents(amount: float | int):
    return int(round(float(amount) * 100))


def get_payphone_public_config():
    settings = _settings()

    if not is_payphone_configured():
        return None

    return {
        "token": settings.payphone_token.strip(),
        "store_id": settings.payphone_store_id.strip(),
    }


def _post_payphone_json(url: str, payload: dict):
    settings = _settings()
    token = settings.payphone_token.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PayPhone no esta configurado.",
        )

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=25) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPhone error: {detail}",
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo conectar con PayPhone: {exc.reason}",
        ) from exc


def confirm_payphone_transaction(transaction_id: int, client_transaction_id: str):
    return _post_payphone_json(
        PAYPHONE_CONFIRM_URL,
        {
            "id": int(transaction_id),
            "clientTxId": client_transaction_id,
        },
    )


def encrypt_card_holder(card_holder_name: str):
    settings = _settings()
    coding_password = settings.payphone_coding_password.strip()

    if not card_holder_name or not coding_password:
        return None

    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dependencia de cifrado PayPhone no instalada.",
        ) from exc

    key = coding_password.encode("utf-8")
    key = key[:32].ljust(32, b"\0")
    iv = b"\0" * 16
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    encrypted = cipher.encrypt(pad(card_holder_name.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def build_token_charge_payload(
    *,
    card_token: str,
    card_holder: str | None,
    encrypted_card_holder: str | None = None,
    document_id: str,
    phone_number: str,
    email: str,
    amount: int,
    client_transaction_id: str,
    reference: str,
    ip_address: str = "127.0.0.1",
):
    settings = _settings()
    display_name = card_holder or "BetterMail User"
    name_parts = display_name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) or name_parts[0]

    return {
        "cardHolder": encrypted_card_holder or encrypt_card_holder(display_name),
        "cardToken": card_token,
        "documentId": document_id,
        "phoneNumber": phone_number,
        "email": email,
        "amount": amount,
        "amountWithoutTax": amount,
        "amountWithTax": 0,
        "tax": 0,
        "clientTransactionId": client_transaction_id,
        "currency": "USD",
        "storeId": settings.payphone_store_id.strip(),
        "optionalParameter": reference,
        "order": {
            "billTo": {
                "address1": "N/A",
                "address2": "",
                "country": "EC",
                "state": "N/A",
                "locality": "N/A",
                "firstName": first_name,
                "lastName": last_name,
                "phoneNumber": f"+{phone_number.lstrip('+')}",
                "email": email,
                "postalCode": "000000",
                "ipAddress": ip_address,
            },
            "lineItems": [
                {
                    "productName": "BetterMail Pro",
                    "unitPrice": amount,
                    "quantity": 1,
                    "totalAmount": amount,
                    "taxAmount": 0,
                    "productSKU": "bettermail-pro-monthly",
                    "productDescription": "Suscripcion mensual BetterMail Pro",
                }
            ],
        },
    }


def charge_payphone_card_token(payload: dict):
    return _post_payphone_json(PAYPHONE_TOKEN_CHARGE_URL, payload)


def is_payphone_charge_approved(response: dict):
    status_code = int(response.get("statusCode") or 0)
    transaction_status = str(response.get("transactionStatus") or "").strip().lower()
    return status_code == 3 and transaction_status == "approved"
