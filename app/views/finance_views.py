# D:\#3xDigital\app\views\finance_views.py
"""
finance_views.py

Módulo responsável pelos endpoints relacionados às funcionalidades financeiras
do sistema 3xDigital, incluindo saldo de afiliados, transações e saques.

Endpoints:
    - GET /finance/balance: Consulta saldo do afiliado
    - GET /finance/transactions: Lista transações do afiliado
    - POST /finance/withdrawals/request: Solicita um saque
    - GET /finance/withdrawals: Lista solicitações de saque
    - PUT /finance/withdrawals/{id}/process: Processa solicitação de saque
    - GET /finance/reports: Gera relatórios financeiros

Regras de Negócio:
    - Afiliados podem consultar apenas seu próprio saldo e transações
    - Administradores podem visualizar dados de qualquer afiliado
    - Saques precisam ser solicitados e aprovados antes de serem processados
    - Relatórios podem ser exportados em diferentes formatos

Dependências:
    - aiohttp para rotas
    - app.services.finance_service para lógica financeira
    - app.middleware.authorization_middleware para autenticação
"""

import datetime
import io
import csv

from aiohttp import web
from sqlalchemy import select

from app.config.settings import DB_SESSION_KEY
from app.middleware.authorization_middleware import require_role
from app.models.database import Affiliate
from app.services.finance_service import (
    get_or_create_balance,
    update_affiliate_balance_from_sale,
    create_withdrawal_request,
    process_withdrawal_request,
    get_affiliate_transactions,
    get_withdrawal_requests,
    generate_financial_report
)

# Definição das rotas
routes = web.RouteTableDef()


@routes.get('/finance/balance')
@require_role(['admin', 'affiliate'])
async def get_affiliate_balance(request: web.Request) -> web.Response:
    """
    Retorna o saldo atual do afiliado autenticado.
    
    Se o usuário for administrador e fornecer affiliate_id na query, 
    retorna o saldo do afiliado especificado.
    
    Query params:
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
    
    Returns:
        web.Response: JSON com dados do saldo
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    
    # Determina o afiliado cuja informação será retornada
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Busca ou cria o saldo
    db = request.app[DB_SESSION_KEY]
    balance = await get_or_create_balance(db, affiliate_id)
    
    # Formata a resposta
    response_data = {
        "affiliate_id": affiliate_id,
        "current_balance": balance.current_balance,
        "total_earned": balance.total_earned,
        "total_withdrawn": balance.total_withdrawn,
        "last_updated": balance.last_updated.isoformat() if balance.last_updated else None
    }
    
    return web.json_response(response_data, status=200)


@routes.get('/finance/transactions')
@require_role(['admin', 'affiliate'])
async def get_transactions(request: web.Request) -> web.Response:
    """
    Retorna o extrato de transações do afiliado.
    
    Query params:
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        start_date (str, opcional): Data inicial (formato ISO)
        end_date (str, opcional): Data final (formato ISO)
        type (str, opcional): Filtro por tipo de transação (commission, withdrawal, adjustment)
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)
    
    Returns:
        web.Response: JSON com lista de transações e metadados
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    
    # Parâmetros da query
    page = int(request.query.get('page', 1))
    page_size = int(request.query.get('page_size', 20))
    
    # Filtros de data
    start_date = None
    end_date = None
    
    if 'start_date' in request.query:
        try:
            start_date = datetime.datetime.fromisoformat(request.query.get('start_date'))
        except ValueError:
            pass
    
    if 'end_date' in request.query:
        try:
            end_date = datetime.datetime.fromisoformat(request.query.get('end_date'))
        except ValueError:
            pass
    
    # Filtro de tipo
    transaction_type = request.query.get('type')
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém as transações
    db = request.app[DB_SESSION_KEY]
    transactions, total_count = await get_affiliate_transactions(
        db, affiliate_id, start_date, end_date, transaction_type, page, page_size
    )
    
    # Formata a resposta
    transaction_data = []
    for t in transactions:
        transaction_data.append({
            "id": t.id,
            "type": t.type,
            "amount": t.amount,
            "description": t.description,
            "reference_id": t.reference_id,
            "date": t.transaction_date.isoformat() if t.transaction_date else None
        })
    
    response_data = {
        "transactions": transaction_data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }
    
    return web.json_response(response_data, status=200)


@routes.post('/finance/withdrawals/request')
@require_role(['affiliate'])
async def request_withdrawal(request: web.Request) -> web.Response:
    """
    Cria uma nova solicitação de saque para o afiliado.
    
    JSON de entrada:
        {
            "amount": 100.00,            # Valor solicitado
            "payment_method": "pix",     # Método de pagamento
            "payment_details": "{\"key\": \"meu@email.com\"}"  # Detalhes do pagamento
        }
    
    Returns:
        web.Response: JSON com dados da solicitação ou erro
    """
    user_id = request["user"]["id"]
    
    # Busca o afiliado associado ao usuário
    db = request.app[DB_SESSION_KEY]
    result = await db.execute(
        select(Affiliate).where(Affiliate.user_id == user_id)
    )
    affiliate = result.scalar_one_or_none()
    
    if not affiliate:
        return web.json_response(
            {"error": "Usuário não é um afiliado"},
            status=403
        )
    
    # Verifica se o afiliado está aprovado
    if affiliate.request_status != 'approved':
        return web.json_response(
            {"error": "Seu status de afiliado ainda não foi aprovado"},
            status=403
        )
    
    # Obtém os dados da requisição
    try:
        data = await request.json()
        
        # Validação básica
        if 'amount' not in data or not isinstance(data['amount'], (int, float)) or data['amount'] <= 0:
            return web.json_response(
                {"error": "Valor de saque inválido"},
                status=400
            )
        
        if 'payment_method' not in data or not data['payment_method']:
            return web.json_response(
                {"error": "Método de pagamento é obrigatório"},
                status=400
            )
        
        if 'payment_details' not in data or not data['payment_details']:
            return web.json_response(
                {"error": "Detalhes de pagamento são obrigatórios"},
                status=400
            )
        
        # Cria a solicitação
        success, message, withdrawal = await create_withdrawal_request(
            db,
            affiliate.id,
            float(data['amount']),
            data['payment_method'],
            data['payment_details']
        )
        
        if not success:
            return web.json_response(
                {"error": message},
                status=400
            )
        
        # Resposta de sucesso
        return web.json_response({
            "message": "Solicitação de saque criada com sucesso",
            "withdrawal_id": withdrawal.id,
            "status": withdrawal.status,
            "amount": withdrawal.amount,
            "requested_at": withdrawal.requested_at.isoformat() if withdrawal.requested_at else None
        }, status=201)
        
    except ValueError as e:
        return web.json_response(
            {"error": f"Dados inválidos: {str(e)}"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Erro ao processar solicitação: {str(e)}"},
            status=500
        )


@routes.get('/finance/withdrawals')
@require_role(['admin', 'affiliate'])
async def list_withdrawals(request: web.Request) -> web.Response:
    """
    Lista as solicitações de saque do afiliado ou de todos os afiliados (para admins).
    
    Query params:
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        status (str, opcional): Filtro por status (pending, approved, rejected, paid)
        page (int, opcional): Página de resultados (padrão: 1)
        page_size (int, opcional): Tamanho da página (padrão: 20)
    
    Returns:
        web.Response: JSON com lista de solicitações e metadados
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    
    # Parâmetros da query
    page = int(request.query.get('page', 1))
    page_size = int(request.query.get('page_size', 20))
    status = request.query.get('status')
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e não especificou um afiliado, retorna todos
    if user_role == 'admin':
        if 'affiliate_id' in request.query:
            affiliate_id = int(request.query.get('affiliate_id'))
    else:
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Obtém as solicitações
    db = request.app[DB_SESSION_KEY]
    withdrawals, total_count = await get_withdrawal_requests(
        db, affiliate_id, status, page, page_size
    )
    
    # Formata a resposta
    withdrawal_data = []
    for w in withdrawals:
        withdrawal_data.append({
            "id": w.id,
            "affiliate_id": w.affiliate_id,
            "amount": w.amount,
            "status": w.status,
            "payment_method": w.payment_method,
            "payment_details": w.payment_details,
            "requested_at": w.requested_at.isoformat() if w.requested_at else None,
            "processed_at": w.processed_at.isoformat() if w.processed_at else None,
            "admin_notes": w.admin_notes if user_role == 'admin' else None
        })
    
    response_data = {
        "withdrawals": withdrawal_data,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    }
    
    return web.json_response(response_data, status=200)


@routes.put('/finance/withdrawals/{withdrawal_id}/process')
@require_role(['admin'])
async def process_withdrawal_request_endpoint(request: web.Request) -> web.Response:
    """
    Processa uma solicitação de saque, aprovando-a, rejeitando-a ou marcando-a como paga.

    Args:
        request (web.Request): Requisição web contendo o ID do saque e o status desejado.

    Returns:
        web.Response: Resposta com detalhes da operação realizada.
    """
    try:
        withdrawal_id = int(request.match_info['withdrawal_id'])
        session = request.app[DB_SESSION_KEY]
        
        # Verifica o ID da solicitação
        if not withdrawal_id:
            return web.json_response({"error": "ID da solicitação é obrigatório"}, status=400)
        
        # Recupera dados do corpo da requisição
        data = await request.json()
        
        # Verifica o status informado
        status = data.get('status')
        if not status or status not in ['approved', 'rejected', 'paid']:
            return web.json_response(
                {"error": "Status inválido. Deve ser 'approved', 'rejected' ou 'paid'."}, 
                status=400
            )
            
        admin_notes = data.get('admin_notes', '')
        
        # Processa a solicitação
        success, message, transaction = await process_withdrawal_request(
            session, 
            withdrawal_id, 
            status, 
            admin_notes
        )
        
        if not success:
            return web.json_response({"error": message}, status=400)
            
        # Monta resposta
        response = {
            "message": f"Solicitação de saque {status}",
            "withdrawal_id": withdrawal_id,
            "status": status
        }
        
        # Adiciona detalhes da transação, se houver
        if transaction:
            response["transaction"] = {
                "id": transaction.id,
                "amount": float(transaction.amount),
                "type": transaction.type,
                "created_at": transaction.transaction_date.isoformat()
            }
            
        return web.json_response(response, status=200)
        
    except ValueError as e:
        return web.json_response({"error": f"Valor inválido: {str(e)}"}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return web.json_response({"error": f"Erro ao processar solicitação: {str(e)}"}, status=500)


@routes.get('/finance/reports')
@require_role(['admin', 'affiliate'])
async def get_financial_report(request: web.Request) -> web.Response:
    """
    Gera relatórios financeiros detalhados.
    
    Query params:
        affiliate_id (int, opcional): ID do afiliado (apenas para admins)
        start_date (str, opcional): Data inicial (formato ISO)
        end_date (str, opcional): Data final (formato ISO)
        format (str, opcional): Formato de saída (json, csv) - padrão: json
    
    Returns:
        web.Response: Relatório financeiro no formato solicitado
    """
    user_id = request["user"]["id"]
    user_role = request["user"]["role"]
    
    # Determina o afiliado
    affiliate_id = None
    
    # Se for admin e especificou um afiliado
    if user_role == 'admin' and 'affiliate_id' in request.query:
        affiliate_id = int(request.query.get('affiliate_id'))
    elif user_role != 'admin':
        # Busca o afiliado associado ao usuário
        db = request.app[DB_SESSION_KEY]
        result = await db.execute(
            select(Affiliate.id).where(Affiliate.user_id == user_id)
        )
        affiliate = result.scalar_one_or_none()
        
        if not affiliate:
            return web.json_response(
                {"error": "Usuário não é um afiliado"},
                status=403
            )
        
        affiliate_id = affiliate
    
    # Filtros de data
    start_date = None
    end_date = None
    
    if 'start_date' in request.query:
        try:
            start_date = datetime.datetime.fromisoformat(request.query.get('start_date'))
        except ValueError:
            pass
    
    if 'end_date' in request.query:
        try:
            end_date = datetime.datetime.fromisoformat(request.query.get('end_date'))
        except ValueError:
            pass
    
    # Formato de saída
    output_format = request.query.get('format', 'json').lower()
    if output_format not in ['json', 'csv']:
        output_format = 'json'
    
    # Gera o relatório
    db = request.app[DB_SESSION_KEY]
    report_data = await generate_financial_report(db, affiliate_id, start_date, end_date)
    
    # Retorna no formato solicitado
    if output_format == 'json':
        return web.json_response(report_data, status=200)
    else:  # csv
        # Prepara o CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        header = ["Métrica", "Valor"]
        writer.writerow(header)
        
        # Período
        writer.writerow(["Período Início", report_data["periodo"]["start"]])
        writer.writerow(["Período Fim", report_data["periodo"]["end"]])
        
        # Comissões
        writer.writerow(["Comissões - Total", report_data["comissoes"]["total"]])
        writer.writerow(["Comissões - Quantidade", report_data["comissoes"]["count"]])
        
        # Saques
        writer.writerow(["Saques - Total", report_data["saques"]["total"]])
        writer.writerow(["Saques - Quantidade", report_data["saques"]["count"]])
        writer.writerow(["Saques Pendentes - Total", report_data["saques"]["pendentes"]["total"]])
        writer.writerow(["Saques Pendentes - Quantidade", report_data["saques"]["pendentes"]["count"]])
        writer.writerow(["Saques Aprovados - Total", report_data["saques"]["aprovados"]["total"]])
        writer.writerow(["Saques Aprovados - Quantidade", report_data["saques"]["aprovados"]["count"]])
        writer.writerow(["Saques Pagos - Total", report_data["saques"]["pagos"]["total"]])
        writer.writerow(["Saques Pagos - Quantidade", report_data["saques"]["pagos"]["count"]])
        writer.writerow(["Saques Rejeitados - Total", report_data["saques"]["rejeitados"]["total"]])
        writer.writerow(["Saques Rejeitados - Quantidade", report_data["saques"]["rejeitados"]["count"]])
        
        # Informações do afiliado (se aplicável)
        if "affiliate" in report_data:
            writer.writerow([""])
            writer.writerow(["Afiliado - ID", report_data["affiliate"]["id"]])
            writer.writerow(["Afiliado - Nome", report_data["affiliate"]["name"]])
            writer.writerow(["Afiliado - Email", report_data["affiliate"]["email"]])
            writer.writerow(["Afiliado - Código de Referência", report_data["affiliate"]["referral_code"]])
            writer.writerow(["Afiliado - Taxa de Comissão", report_data["affiliate"]["commission_rate"]])
            writer.writerow(["Afiliado - Saldo Atual", report_data["affiliate"]["current_balance"]])
            writer.writerow(["Afiliado - Total Ganho", report_data["affiliate"]["total_earned"]])
            writer.writerow(["Afiliado - Total Sacado", report_data["affiliate"]["total_withdrawn"]])
        
        output.seek(0)
        
        # Define o nome do arquivo para download
        filename = f"relatorio-financeiro-{'afiliado-'+str(affiliate_id) if affiliate_id else 'geral'}-{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        
        # Retorna o CSV
        return web.Response(
            body=output.getvalue(),
            headers={
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )