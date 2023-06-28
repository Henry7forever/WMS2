from app.dto import base_resource_fields, delete_success_resp
from app.dto.budget_dto import BudgetDTO
from app.service import budget_service
from app.util.Api_base_resource import customResource
from app.util.OAuthClient import require_oauth
from app.util.enums import enum_budget_type
from app.util.pre_request import pre

api = BudgetDTO.api

@api.route('')
class Budget(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(BudgetDTO.budget_resp_resp_fields_model)
    @pre.catch(post=BudgetDTO.add_budget_req)
    def post(self, params):
        """
            新增預算
        """
        if params.get("budget_type") == enum_budget_type.PILOT.value:
            return {'budget': budget_service.add_pilot_budget(params)}
        return {'budget': budget_service.add_extra_or_additional_budget(params)}

    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(BudgetDTO.budget_resp_resp_fields_model)
    @pre.catch(put=BudgetDTO.update_budget_req)
    def put(self, params):
        """
            修改預算
        """
        return {'budget': budget_service.update_budget(params)}

    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(base_resource_fields)
    @pre.catch(BudgetDTO.delete_budget_req)
    def delete(self, params):
        """
            刪除預算
        """
        budget_service.delete_budget(params.get("id"))
        return delete_success_resp


@api.route('/page')
class BudgetPage(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(BudgetDTO.budget_pagination_resp_fields_model)
    @pre.catch(get=BudgetDTO.get_budget_paginate_by_params_req)
    def get(self, params):
        """
            獲取預算分頁列表
        """
        if params.get("budget_type") is None:
            type_list = enum_budget_type.get_value_list()
            type_list.remove("EXTRA")
            params["budget_type"] = type_list
        return budget_service.get_budget_page_by_params(params, page_index=params['page_index'],
                                                           per_page=params['per_page'])


@api.route('/menu')
class BudgetMenu(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(BudgetDTO.budget_menu_resp_fields_model)
    @pre.catch(get=BudgetDTO.get_budget_menu_req)
    def get(self, params):
        """
            獲取預算選單
        """
        return {'budget_list': budget_service.get_budget_menu_by_params(params)}


@api.route('/synchronize/demand')
class SynchronizeBudgetDemand(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(base_resource_fields)
    @pre.catch(put=BudgetDTO.synchronize_pilot_budget_content_and_demand_req)
    def put(self, params):
        """
            同步需求與數量
        """
        budget_service.synchronize_pilot_budget_demand_with_stock(params.get("id"))


@api.route('/synchronize/unit_price_and_exchange_rate')
class SynchronizeBudgetUnitPriceAndExchangeRate(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(base_resource_fields)
    @pre.catch(put=BudgetDTO.synchronize_pilot_budget_content_and_demand_req)
    def put(self, params):
        """
            同步单價與匯率
        """
        budget_service.synchronize_budget_unit_price_and_currency_and_exchange_rate_with_partnumber_info(params.get("id"))


@api.route('/content/list')
class BudgetContentList(customResource):
    @require_oauth('server')
    # @require_role(contains_any=enum_role.get_name_list())
    @api.marshal_with(BudgetDTO.budget_content_list_resp_fields_model)
    @pre.catch(get=BudgetDTO.get_budget_content_list_req)
    def get(self, params):
        return {'budget_content_list': budget_service.get_budget_content_by_params(params)}



