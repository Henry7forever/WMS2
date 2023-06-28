from copy import deepcopy
from flask_restx import Namespace, fields
from app.dto import base_resource_fields, BasePostStrRule, MyDateTimeFormat, BasePutStrRule, BasePostIntRule, \
    EnumField, BasePutBoolRule, base_paginate_req_params, base_resource_pagination_fields
from app.util.enums import enum_budget_type
from app.util.pre_request import Rule
from app.dto.phase_dto import PhaseDTO
from app.dto.product_dto import ProductDTO

class BudgetDTO(object):
    api = Namespace('預算管理')

    budget_resp_dto = {
        "id": fields.Integer(),
        "name": fields.String(),
        "type": EnumField(attribute='budget_type'),
        "is_lock": fields.Boolean(),
        "product": fields.Nested(ProductDTO.product_resp_dto, attribute="_phase._product"),
        "phase": fields.Nested(PhaseDTO.phase_resp_dto, attribute="_phase"),
        "created_by": fields.String(attribute='creator_name'),
        "created_by_account": fields.String(attribute='creator_account'),
        "updated_by": fields.String(attribute='updater_name'),
        "updated_by_account": fields.String(attribute='updater_account'),
        "created_time": MyDateTimeFormat(attribute='create_time'),
        "updated_time": MyDateTimeFormat(attribute='last_update_time')
    }
    budget_resp_dto['children'] = fields.List(fields.Nested(budget_resp_dto), attribute="_extra_budget_list")


    budget_menu_resp_dto = {
        "id": fields.Integer(),
        "name": fields.String(),
    }

    budget_content_resp_dto = {
        "id": fields.Integer(),
        "partnumber": fields.Nested(PartnumberDTO., attribute="_partnumber"),
        "small_line_name": fields.String(),
        "status": fields.Boolean(),
        "total_purchase_qty": fields.Integer(),
        "additional": fields.Float(),
        "addition": EnumField(),
        "lead_time_lower": fields.Integer(),
        "lead_time_upper": fields.Integer(),
        "buyer": EnumField(),
        "user_dri": fields.String(),
        "user_department": fields.String(),
        "user_department_manager": fields.String(),
        "user_code": fields.String(),
        "apple_counterpart": fields.String(),
        "reimburse_confirm": fields.Boolean(),
        "emergency_purchase": fields.Boolean(),
        "reason_demand": fields.String(),
        "on_hand_qty": fields.Integer(),
        "unit_price": fields.Float(),
        "station_type": EnumField(),
        "station_name": fields.String(),
        "demand_list"
        
        "created_by": fields.String(attribute='creator_name'),
        "created_by_account": fields.String(attribute='creator_account'),
        "updated_by": fields.String(attribute='updater_name'),
        "updated_by_account": fields.String(attribute='updater_account'),
        "created_time": MyDateTimeFormat(attribute='create_time'),
        "updated_time": MyDateTimeFormat(attribute='last_update_time')
    }


    # req
    add_budget_req = {
        "phase_id": BasePostIntRule(),
        "bind_pilot_budget_id": Rule(type=int, dest='pilot_budget_id', required=False),
        "eqlist_task_id": Rule(type=int, dest='source_main_eq_task_id', required=False),
        "name": BasePostStrRule(),
        "type": BasePostStrRule(enum=enum_budget_type.get_value_list(), dest="budget_type")
    }

    update_budget_req = {
        "budget_id": Rule(type=int, dest='id', required=True),
        "name": BasePutStrRule(),
        "is_lock": BasePutBoolRule(),
    }

    delete_budget_req = {
        "budget_id": Rule(type=int, dest='id', location='args', required=True),
    }

    get_budget_paginate_by_params_req = deepcopy(base_paginate_req_params)
    get_budget_paginate_by_params_req.update(
        {
            "phase_id": Rule(type=int, location='args', required=False),
            "type": Rule(type=str, location='args', trim=True, dest='budget_type', required=False, enum=enum_budget_type.get_value_list()),
        }
    )

    get_budget_menu_req = {
        "phase_id": Rule(type=int, location='args', required=True),
        "type": Rule(type=str, location='args', trim=True, dest='budget_type', required=False, enum=enum_budget_type.get_value_list()),
        "is_lock": Rule(type=bool, location='args', required=False),
    }

    synchronize_pilot_budget_content_and_demand_req = {
        "budget_id": Rule(type=int, dest='id', required=True),
    }

    get_budget_content_list_req = {
        "budget_id": Rule(type=int, location='args', required=True),
        "purchase_method": Rule(type=str, multi=True, split=',', location='args', trim=True, required=False),
    }

    __budget_pagination_resp_fields = deepcopy(base_resource_pagination_fields)
    __budget_pagination_resp_fields['result']['budget_list'] = fields.List(fields.Nested(budget_resp_dto), attribute="items")
    budget_pagination_resp_fields_model = api.model('獲取預算分頁列表', __budget_pagination_resp_fields)

    __budget_menu_resp_fields = deepcopy(base_resource_fields)
    __budget_menu_resp_fields['result']['budget_list'] = fields.List(fields.Nested(budget_menu_resp_dto))
    budget_menu_resp_fields_model = api.model('獲取預算選單', __budget_menu_resp_fields)

    __budget_resp_resp_fields = deepcopy(base_resource_fields)
    __budget_resp_resp_fields['result']['budget'] = fields.Nested(budget_resp_dto)
    budget_resp_resp_fields_model = api.model('獲取預算', __budget_resp_resp_fields)




    __budget_content_list_resp_fields = deepcopy(base_resource_fields)
    __budget_content_list_resp_fields['result']['budget_content_list'] = fields.List(fields.Nested(budget_content_resp_dto))
    budget_content_list_resp_fields_model = api.model('獲取預算詳情列表', __budget_content_list_resp_fields)