from app.dto import base_resource_fields, delete_success_resp
from app.dto.eqlist_content_dto import EQListContentDTO
from app.service import eqlist_content_service
from app.util.api_base_resource import customResource
from app.util.decorators import require_role
from app.util.oauth_client import require_oauth
from app.util.enums import enum_role
from app.util.pre_request import pre

api = EQListContentDTO.api


@api.route('')
class EQListContent(customResource):

    @require_oauth('server')
    @require_role(contains_any=[enum_role.DRI])
    @api.marshal_with(EQListContentDTO.eqlist_content_resp_field_model)
    @pre.catch(EQListContentDTO.add_eqlist_content_by_params_req)
    def post(self, params):
        """
            新建EQ回复内容
        """
        return {"result": eqlist_content_service.add_eqlist_content_by_params(params)}

    @require_oauth('server')
    @require_role(contains_any=[enum_role.DRI])
    @api.marshal_with(EQListContentDTO.eqlist_content_resp_field_model)
    @pre.catch(EQListContentDTO.update_eqlist_content_by_params_req)
    def put(self, params):
        """
            编辑EQ回复内容
        """
        return {"result": eqlist_content_service.update_eqlist_content_by_params(params)}

    @require_oauth('server')
    @require_role(contains_any=[enum_role.DRI])
    @api.marshal_with(base_resource_fields)
    @pre.catch(EQListContentDTO.delete_eqlist_content_by_params_req)
    def delete(self, params):
        """
            删除EQ回复的内容
        """
        eqlist_content_service.delete_eqlist_content_by_params(params)
        return delete_success_resp


@api.route('/file')
class EQListContentFile(customResource):

    @require_oauth('server')
    @require_role(contains_any=[enum_role.LL])
    @pre.catch(EQListContentDTO.aggregate_by_station_eqlist_content_params_req)
    def get(self, params):
        """
            获取EQlist文件
        """
        return eqlist_content_service.get_eqlist_file_by_params(params)


@api.route('/record')
class EQListContentAggregation(customResource):

    @require_oauth('server')
    @require_role(contains_any=[enum_role.LL, enum_role.DRI, enum_role.MANAGER])
    @api.marshal_with(EQListContentDTO.eqlist_content_singal_record_resp_field_model)
    @pre.catch(EQListContentDTO.aggregate_by_station_eqlist_content_params_req)
    def get(self, params):
        """
            获取EQlist所有单条记录
        """
        return {"station_list": eqlist_content_service.aggregate_by_station_eqlist_content_by_params(params)}


@api.route('/sub_task')
class EQListContentSubTask(customResource):

    @require_oauth('server')
    @require_role(contains_any=[enum_role.LL, enum_role.DRI, enum_role.MANAGER])
    @api.marshal_with(EQListContentDTO.eqlist_content_sub_task_resp_field_model)
    @pre.catch(EQListContentDTO.eqlist_content_sub_task_by_params_req)
    def get(self, params):
        """
            获取EQlist子任务回复内容
        """
        return {"reply_target_list": eqlist_content_service.get_sub_task_reply_target_by_params(params)}
