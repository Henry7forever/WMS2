import collections

from sqlalchemy import and_

from app import db
from app.model.budget_model import Budget
from app.model.budget_content_model import BudgetContent
from app.model.budget_demand_model import BudgetDemand
from app.model.main_task_model import MainTask
from app.model.partnumber_model import Partnumber
from app.service import public_menu_service
from app.service.main_task_service import get_eq_task_partnumber_demand_list_by_main_task_id
from app.util.Api_exceptions import UnprocessableContentError, NotFoundError
from app.util.enums import enum_budget_type, enum_task_type


# 1.初版預算只過度EQ匯總後Total Demand Q'ty > On Hand Q'ty 之partnumber
# 2.使用預算產品信息與良品種類去算On Hand Q'ty
def add_pilot_budget(params):
    new_budget = Budget.add_model_by_params(params)
    # new_budget.validate_source_main_eq_sub_tasks_all_approved()
    #  1.過渡EQ之partnumber匯總清單，
    #  2.建立預算詳情
    #  3.建立function需求數量信息

    __insert_or_update_all_budget_content_by_pilot_budget_id(new_budget.id)

    db.session.commit()
    return new_budget


def __get_fresh_partnumber_demand_list_by_eq_main_task_id(eq_main_task_id):
    eq_main_task = MainTask.get_model_by_id(eq_main_task_id)

    if eq_main_task is None:
        raise NotFoundError(msg=f'eq task not found')

    if eq_main_task.task_type is not enum_task_type.EQ_LIST:
        raise UnprocessableContentError(msg=f'source must be eq task type')

    migrate_partnumber_demand_list = []

    partnumber_demand_list = get_eq_task_partnumber_demand_list_by_main_task_id(eq_main_task.id)
    for pn_demand in partnumber_demand_list:
        partnumber_defective_qty = ((pn_demand.get("partnumber")).aggregate_by_product_non_defective_qty).get(
            eq_main_task._phase._product.fx_code)
        partnumber_total_demand_qty = sum(
            [_function_demand['demand_qty'] for _function_demand in pn_demand.get("function_demand_list")])
        total_purchase_qty = partnumber_total_demand_qty - partnumber_defective_qty
        if total_purchase_qty > 0:
            migrate_partnumber_demand_list.append(
                dict(pn_demand, total_purchase_qty=total_purchase_qty, on_hand_qty=partnumber_defective_qty)
            )

    return migrate_partnumber_demand_list


def add_extra_or_additional_budget(params):
    new_budget = Budget.add_model_by_params(params)
    db.session.commit()
    return new_budget


def update_budget(params):
    _budget = Budget.get_model_by_id(params.get("id")).update_model_by_params(params)
    db.session.commit()
    return _budget


def delete_budget(budget_id):
    Budget.delete_model_by_id(budget_id)
    db.session.commit()


def get_budget_page_by_params(params={},
                              page_index=1,
                              per_page=15,
                              orders=collections.OrderedDict({"create_time": "desc"})):
    return Budget.get_model_list_by_params_paginate(params=params,
                                                    page_index=page_index,
                                                    per_page=per_page,
                                                    orders=orders)


def get_budget_menu_by_params(params={}, orders=collections.OrderedDict({"create_time": "desc"})):
    budget_list = Budget.get_model_list_by_params(params, orders=orders)
    return [{"id": _budget.id, "name": _budget.name} for _budget in budget_list]


# 1.只有初版預算才顯示同步需求與庫存
# 2.只有LL有權限操作此功能
# 3.只有源頭eq主任物之全部子任務已通過才能使用此功能
# 4.刷新demand qty & pn清單(使用預算產品信息與良品種類去算On Hand Q'ty, 篩選Total Demand Q'ty > On Hand Q'ty 之partnumber) & on_hand_qty
# 5.只有在非鎖定狀態且編輯模式才有此功能
def synchronize_pilot_budget_demand_with_stock(pilot_budget_id):
    pilot_budget = Budget.get_model_by_id(pilot_budget_id)

    if pilot_budget.budget_type is not enum_budget_type.PILOT:
        raise UnprocessableContentError(msg=f'source must be pilot budget')
    pilot_budget.validate_source_main_eq_sub_tasks_all_approved()

    fresh_partnumber_demand_list = __get_fresh_partnumber_demand_list_by_eq_main_task_id(
        pilot_budget.source_main_eq_task_id)
    fresh_partnumber_id_list = [(i.get("partnumber")).id for i in fresh_partnumber_demand_list]

    delete_pn_id_list = []
    for old_budget_content in pilot_budget._budget_content_list:
        if old_budget_content.partnumber_id not in fresh_partnumber_id_list:
            delete_pn_id_list.append(old_budget_content.partnumber_id)
        else:
            fresh_function_demand_list = next(
                filter(lambda x: x.get("partnumber").id == old_budget_content.partnumber_id,
                       fresh_partnumber_demand_list)).get("function_demand_list")
            fresh_function_list = [(i.get("function")) for i in fresh_function_demand_list]
            delete_function_list = []
            for old_budget_demand in old_budget_content._budget_demand_list:
                if old_budget_demand.fucntion not in fresh_function_list:
                    delete_function_list.append(old_budget_demand.function)
            for delete_function in delete_function_list:
                BudgetDemand.delete_models_by_params(
                    {"function": delete_function, "budget_content_id": old_budget_content.id})
            db.session.flush()
    for delete_pn_id in delete_pn_id_list:
        BudgetContent.delete_models_by_params({"partnumber_id": delete_pn_id, "budget_id": pilot_budget.id})
    db.session.flush()

    __insert_or_update_all_budget_content_by_pilot_budget_id(pilot_budget.id)

    db.session.commit()
    return pilot_budget


def __insert_or_update_all_budget_content_by_pilot_budget_id(pilot_budget_id):
    pilot_budget = Budget.get_model_by_id(pilot_budget_id)

    fresh_partnumber_demand_list = __get_fresh_partnumber_demand_list_by_eq_main_task_id(
        pilot_budget.source_main_eq_task_id)

    for fresh_partnumber_demand in fresh_partnumber_demand_list:
        _pn = fresh_partnumber_demand.get("partnumber")

        # TODO: 購買須滿足最小架站要求
        update_budget_content_ignore_properties = ["partnumber_id", "budget_id", "total_purchase_qty", "unit_price", "unit_price_currency",
         "exchange_rate_to_usd"]
        existed_budget_content = BudgetContent.get_model_by_params({"partnumber_id": _pn.id, "budget_id": pilot_budget.id})
        if existed_budget_content is not None and fresh_partnumber_demand.get("total_purchase_qty") > existed_budget_content.total_purchase_qty:
            update_budget_content_ignore_properties.remove("total_purchase_qty")

        _budget_content = BudgetContent.insert_or_update({
            "partnumber_id": _pn.id,
            "budget_id": pilot_budget.id,
            "total_purchase_qty": fresh_partnumber_demand.get("total_purchase_qty"),
            "on_hand_qty": fresh_partnumber_demand.get("on_hand_qty"),
            "unit_price": _pn.price,
            "unit_price_currency": _pn.currency,
            "exchange_rate_to_usd": public_menu_service.get_exchange_rate_to_usd(_pn.currency)
        }, ignore_update=update_budget_content_ignore_properties)
        db.session.flush()
        for _function_demand in fresh_partnumber_demand.get("function_demand_list"):
            BudgetDemand.insert_or_update({
                "function": _function_demand.get("function"),
                "demand_qty": _function_demand.get("demand_qty"),
                "budget_content_id": _budget_content.id,
            }, ignore_update=["budget_content_id", "function"])
            db.session.flush()

    return pilot_budget


# 1.刷新unit price
# 2.只有在非鎖定狀態且編輯模式才有此功能
# 3.只有LL有權限操作此功能
def synchronize_budget_unit_price_and_currency_and_exchange_rate_with_partnumber_info(budget_id):
    target_budget = Budget.get_model_by_id(budget_id)
    for _budget_content in target_budget._budget_content_list:
        _budget_content.unit_price = _budget_content._partnumber.price
        _budget_content.unit_price_currency = _budget_content._partnumber.currency
        _budget_content.exchange_rate_to_usd = public_menu_service.get_exchange_rate_to_usd(_budget_content._partnumber.currency)
    db.session.commit()
    return target_budget


def get_budget_file_by_type_and_id(budget_id, types=enum_budget_type.get_value_list()):
    # TODO: implement file generate

    return


def get_budget_content_by_params(params):
    budget_content_list_query = BudgetContent.query.join(Partnumber.payment_method).filter(
             BudgetContent.budget_id == params.get("budget_id"))
    if params.get("purchase_method") is not None and len(params.get("purchase_method") > 0):
        budget_content_list_query = budget_content_list_query.filter(Partnumber.payment_method.in_(params.get("purchase_method")))
    return budget_content_list_query.all()


# manually add budget content
def add_budget_content(params):

    __validate_budget_content_manually_modified_forbidden(params.get("budget_id"))

    # TODO: prepare insert params: ["on_hand_qty", "unit_price", "unit_price_currency", "exchange_rate_to_usd"]
    _pn = Partnumber.get_model_by_id(params.get("partnumber_id"))
    params.upadte({
        "on_hand_qty": ,
        "unit_price": _pn.price,
        "unit_price_currency": _pn.currency,
        "exchange_rate_to_usd": ,
    })

    new_budget_content = BudgetContent.add_model_by_params(params)
    db.session.commit()
    return new_budget_content


def update_budget_content(params):
    _budget_content = Budget.get_model_by_id(params.get("id")).update_model_by_params(params)
    db.session.commit()
    return _budget_content


def delete_budget_content(budget_content_id):
    BudgetContent.delete_model_by_id(budget_content_id)
    db.session.commit()


def delete_budget_demand(budget_demand_id):
    target_budget_demand = BudgetDemand.get_model_by_id(budget_demand_id)
    target_budget_content = target_budget_demand._budget_content
    __validate_budget_demand_manually_modified_forbidden(target_budget_content.id)
    BudgetDemand.delete_model_by_id(budget_demand_id)
    db.session.flush()

    if len(target_budget_content._budget_demand_list) <= 0:
        BudgetContent.delete_model_by_id(target_budget_content.id)

    db.session.commit()


def insert_or_update_budget_demand(params):
    __validate_budget_demand_manually_modified_forbidden(params.get("budget_content_id"))
    _budget_content = BudgetDemand.insert_or_update(params, ignore_update=["budget_content_id", "function"])
    db.session.commit()
    return _budget_content



def __validate_budget_demand_manually_modified_forbidden(budget_content_id):
    if BudgetContent.get_model_by_id(budget_content_id)._budget.budget_type == enum_budget_type.PILOT:
        raise UnprocessableContentError(msg=f'pilot budget can not manually modify budget content')


def __validate_budget_content_manually_modified_forbidden(budget_id):
    if Budget.get_model_by_id(budget_id).budget_type == enum_budget_type.PILOT:
        raise UnprocessableContentError(msg=f'pilot budget can not manually add budget content')


