import math
from io import BytesIO

import pandas as pd
from sqlalchemy import func

from app import db
from app.lib.excelLib import el
from app.model.connect_eqlist_content_partnumber_model import ConnectEQListContentPartnumber
from app.model.eqlist_content_model import EQListContent
from app.model.main_task_model import MainTask
from app.model.partnumber_model import Partnumber
from app.model.reply_target_model import ReplyTarget
from app.model.station_model import Station
from app.model.sub_task_model import SubTask
from app.util.pre_request.utils import _Missing


def add_eqlist_content_by_params(params):
    _eqlist_content = EQListContent.add_model_by_params({
        "reply_target_id": params['target_id'],
        "station_bom_qty": params['bom_number'],
        "station_name": params['station_name'],
        "name": params['bom_name'],
        "uph": params['uph'],
        "priority": params['priority'],
        "function": params['function']
    })

    for _partnumber_obj in params['partnumber_list']:
        ConnectEQListContentPartnumber.add_model_by_params({
            "eqlist_content_id": _eqlist_content.id,
            "partnumber_id": _partnumber_obj['partnumber_id'],
            "bom_ratio": _partnumber_obj['ratio'],
            "backup_ratio": _partnumber_obj['back_up_ratio']
        })

    db.session.commit()
    return _eqlist_content


def update_eqlist_content_by_params(params):
    _eqlist_content = EQListContent.get_model_by_id(params['eqlist_content_id']).update_model_by_params({
        "station_bom_qty": params['bom_number'],
        "station_name": params['station_name'],
        "name": params['bom_name'],
        "uph": params['uph'],
        "priority": params['priority'],
        "function": params['function']
    })
    if params['partnumber_list'] != _Missing:
        _partnumber_list = {_connectEQListContentPartnumber.partnumber_id: {
            "ratio": _connectEQListContentPartnumber.bom_ratio,
            "backup_ratio": _connectEQListContentPartnumber.backup_ratio
        } for _connectEQListContentPartnumber in _eqlist_content._station_bom_partnumbers}

        _req_partnumber_list = {_partnumber_obj['partnumber_id']: {
            "bom_ratio": _partnumber_obj['ratio'],
            "backup_ratio": _partnumber_obj['back_up_ratio']
        } for _partnumber_obj in params['partnumber_list']}

        _remove_partnumber_list = list(set(_partnumber_list.keys()).difference(_req_partnumber_list.keys()))
        _add_partnumber_list = list(set(_req_partnumber_list.keys()).difference(_partnumber_list.keys()))
        _add_partnumber_dict = {k: v for k, v in _req_partnumber_list.items() if k in _add_partnumber_list}
        _update_partnumber_dict = {k: v for k, v in _req_partnumber_list.items() if k not in _add_partnumber_list}

        # remove
        ConnectEQListContentPartnumber.delete_models_by_params({"eqlist_content_id": _eqlist_content.id, "partnumber_id": _remove_partnumber_list})

        # add
        for _add_partnumber_id, val in _add_partnumber_dict.items():
            val['eqlist_content_id'] = _eqlist_content.id
            val['partnumber_id'] = _add_partnumber_id
            ConnectEQListContentPartnumber.add_model_by_params(val)

        # update
        for _update_partnumber_id, val in _update_partnumber_dict.items():
            ConnectEQListContentPartnumber.get_model_by_params({"eqlist_content_id": _eqlist_content.id, "partnumber_id": _update_partnumber_id}).update_model_by_params(val)

    db.session.commit()
    return _eqlist_content


def delete_eqlist_content_by_params(params):
    EQListContent.delete_model_by_id(params['eqlist_content_id'])
    db.session.commit()


def aggregate_by_station_eqlist_content_by_params(params):
    rst = MainTask._get_model_sql_by_params({"id": params['main_task_id']}) \
        .join(SubTask) \
        .join(ReplyTarget) \
        .join(EQListContent) \
        .join(ConnectEQListContentPartnumber) \
        .with_entities(ReplyTarget.target_id,
                       ConnectEQListContentPartnumber.partnumber_id,
                       func.sum(EQListContent.station_bom_qty * ConnectEQListContentPartnumber.bom_ratio),
                       func.sum(EQListContent.station_bom_qty * ConnectEQListContentPartnumber.bom_ratio * ConnectEQListContentPartnumber.backup_ratio)) \
        .group_by(ReplyTarget.target_id, ConnectEQListContentPartnumber.partnumber_id) \
        .all()

    # [(1, 2774, Decimal('15'), Decimal('30')), (1, 2775, Decimal('10'), Decimal('20'))]
    station_dict = {}
    for i in rst:
        station_id = i[0]
        partnumber_id = i[1]
        need_qty = int(i[2])
        back_up_qty = int(i[3])
        parmas = {
            "partnumber": Partnumber.get_model_by_id(partnumber_id),
            "need_qty": need_qty,
            "back_up_qty": math.ceil(back_up_qty / 100)
        }

        if station_dict.get(station_id):
            station_dict[station_id].append(parmas)
        else:
            station_dict[station_id] = []
            station_dict[station_id].append(parmas)

    station_list = [{
        "station": Station.get_model_by_id(k),
        "partnumber_list": v
    } for k, v in station_dict.items()]

    return station_list


def get_sub_task_reply_target_by_params(params):
    reply_targets_list = []
    for _subTask in SubTask.get_model_list_by_params(params):
        reply_targets_list.extend(_subTask._reply_targets)

    return reply_targets_list


def aggregate_by_big_line_eqlist_content_by_params(params):
    station_dict_list = aggregate_by_station_eqlist_content_by_params(params)
    big_line_dict_list = {}
    for _station_dict in station_dict_list:
        _big_line = _station_dict['station']._small_line._big_line
        if big_line_dict_list.get(_big_line):
            big_line_dict_list[_big_line].append(_station_dict)
        else:
            big_line_dict_list[_big_line] = []
            big_line_dict_list[_big_line].append(_station_dict)

    return [{
        "big_line": k,
        "station_list": v
    } for k, v in big_line_dict_list.items()]


def get_eqlist_file_by_params(params):
    big_line_list = aggregate_by_big_line_eqlist_content_by_params(params)
    # [{'big_line': <BigLine 1>, 'station_list': [{'station': <Station 1>, 'partnumber_list': [{'partnumber': <Partnumber 2774>, 'need_qty': 5, 'back_up_qty': 10}]}]}, {'big_line': <BigLine 2>, 'station_list': [{'station': <Station 2>, 'partnumber_list': [{'partnumber': <Partnumber 2774>, 'need_qty': 10, 'back_up_qty': 20}, {'partnumber': <Partnumber 2775>, 'need_qty': 10, 'back_up_qty': 20}]}]}]

    bio = BytesIO()
    writer = pd.ExcelWriter(bio, engine="openpyxl")

    if len(big_line_list) == 0:
        df = pd.DataFrame()
        df.to_excel(writer, sheet_name="sheet")
        writer.save()
    else:
        for big_line_dict in big_line_list:
            big_line = big_line_dict['big_line']
            data_list = []
            for staion_dict in big_line_dict['station_list']:
                _station = staion_dict['station']
                for partnumber in staion_dict['partnumber_list']:
                    _partnumber = partnumber['partnumber']
                    need_qty = partnumber['need_qty']
                    back_up_qty = partnumber['back_up_qty']
                    on_hand_qty = _partnumber.get_non_defective_qty_by_product_name(big_line._phase._product.fx_code)
                    data_list.append({
                        "Team": _station.function,
                        "Line": _station._small_line.name,
                        "Station": _station.display_name,
                        "Equipment(English)": _partnumber.en_name,
                        "Equipment(Chinese)": _partnumber.zh_name,
                        "Vendor": _partnumber._vendor_item.item_name,
                        "Spec/Model/Drawing Number": _partnumber._spec_item.item_name,
                        "Q'ty/Station": need_qty,
                        "Station/Line": 1,
                        "Line Q'ty": 1,
                        "NeedQ'ty": need_qty,
                        "Back Up Q'ty": back_up_qty,
                        "Total Q'ty Demand": need_qty + back_up_qty,
                        "On-hand Q'ty": on_hand_qty,
                        "Delta": on_hand_qty - (need_qty + back_up_qty),
                        "Dept.": "NPI-HWTE",
                        "Remark\n（治具/設備需要升級請在此欄位備註）": ""
                    })
            df = pd.DataFrame(data_list)
            el.to_excel_auto_column_weight(df=df, writer=writer, sheet_name=big_line.floor)
            writer.save()
            # df.to_excel(writer, sheet_name=big_line.floor)
    _main_task = MainTask.get_model_by_id({"id": params['main_task_id']})
    return el.make_excel_response(bio, file_name=f"{_main_task._phase._product.fx_code} {_main_task._phase.name} Build FATP EQ List.xlsx")
