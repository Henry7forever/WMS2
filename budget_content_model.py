import json

from sqlalchemy.ext.hybrid import hybrid_property

from sqlalchemy import UniqueConstraint, event
from sqlalchemy.orm import validates, backref

from app import db
from app.model import createAndUpdateMixin, base_model
from app.model.budget_model import Budget
from app.model.public_menu_model import PublicMenu
from app.model.station_model import Station
from app.util.api_exceptions import ForbiddenError
from app.util.current_user import current_user
from app.util.enums import enum_confirm, enum_role


class BudgetContent(db.Model, createAndUpdateMixin, base_model):
    __tablename__ = 'wms_budget_content'
    __table_args__ = (
        UniqueConstraint("partnumber_id", "budget_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    partnumber_id = db.Column(db.ForeignKey("wms_partnumber.id", ondelete="CASCADE"), nullable=False)
    budget_id = db.Column(db.ForeignKey("wms_budget.id", ondelete="CASCADE"), nullable=False)
    part_no = db.Column(db.String(24), nullable=False, default="料號新建中")
    # TODO: to be validated
    addition = db.Column(db.String(32), nullable=True)
    lead_time_weeks_low = db.Column(db.Integer, nullable=True)
    lead_time_weeks_high = db.Column(db.Integer, nullable=True)
    # TODO: to be validated
    buyer = db.Column(db.String(32), nullable=True)
    # TODO: to be validated
    user_dri = db.Column(db.String(16), nullable=True)
    # TODO: to be validated
    user_dept = db.Column(db.String(32), nullable=True)
    # TODO: to be validated
    user_dept_manager = db.Column(db.String(16), nullable=True)
    apple_counterpart = db.Column(db.String(64), nullable=True)
    reimburse_customer_check = db.Column(db.Enum(enum_confirm), nullable=True)
    emergency_purchase_submit = db.Column(db.Enum(enum_confirm), nullable=True)
    purchase_reason = db.Column(db.String(512)
                                , nullable=True
                                # , default="固定填寫格式:\n1. On-hand: 0\n2. New buy: 0\n3. 具体用途：XXX\n4. 是否可借用：是/否\n5. 新购原因：設計變更"
                                )
    total_purchase_qty = db.Column(db.Integer, nullable=False, default=0)
    on_hand_qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.String(16), nullable=False)
    # TODO: to be validated
    unit_price_currency = db.Column(db.String(16), nullable=False)
    exchange_rate_to_usd = db.Column(db.String(7), nullable=False)

    _budget_demand_list = db.relationship("BudgetDemand", cascade="all,delete")
    # _partnumber = db.relationship("Partnumber", backref=backref("_budget_content_list", cascade="all,delete"))
    _partnumber = db.relationship("Partnumber")
    _budget = db.relationship("Budget")

    @hybrid_property
    def partnumber_station_mapping_name(self):
        if self._partnumber._station_item.item_name == "通用":
            return "ALL"
        return self._partnumber._station_item.item_name

    @hybrid_property
    def partnumber_category(self):
        category_menu = PublicMenu.get_model_by_params(params={"menu_name": "Category"})._children
        target_category = next(filter(
            lambda _category: _category.menu_name == (self._partnumber._asset_category_item.item_name),
            category_menu))
        return json.loads(target_category.config).get("budget_category")

    @hybrid_property
    def user_code(self):
        if self.user_dept is None:
            return None
        usercode_menu = PublicMenu.get_model_by_params(params={"menu_name": "UserCode"})._children
        usercode_list = [{"user_code": user_code.menu_name, "config": json.loads(user_code.config)} for user_code in
                         usercode_menu]
        target_usercode = next(filter(
            lambda user_code: user_code["config"]["payment"] == self._partnumber.payment_method
                              and user_code["config"]["user_dept"] == self.user_dept, usercode_list))
        return target_usercode.get("user_code")

    @hybrid_property
    def small_line_name(self):
        if self.partnumber_station_mapping_name == "ALL":
            return "ALL"
        _big_lines = self._budget._phase._big_lines
        for bl in _big_lines:
            for sl in bl._small_lines:
                target_station = Station.get_model_by_params(
                    params={"small_line_id": sl.id, "display_name": self._partnumber._station_item.item_name}, check=False)
                if target_station is not None:
                    return sl.name
        return "ALL"

    @hybrid_property
    def reply_status(self):
        if self.addition is not None \
                and self.lead_time_weeks_low is not None \
                and self.lead_time_weeks_high is not None \
                and self.buyer is not None \
                and self.user_dri is not None \
                and self.user_dept is not None \
                and self.user_dept_manager is not None \
                and self.apple_counterpart is not None \
                and self.reimburse_customer_check is not None \
                and self.emergency_purchase_submit is not None \
                and self.purchase_reason is not None:
            return True
        return False

    @hybrid_property
    def total_demand_qty(self):
        return sum([i.demand_qty for i in self._budget_demand_list])

    @hybrid_property
    def usd_unit_price(self):
        return float(self.unit_price) * float(self.exchange_rate_to_usd)

    @hybrid_property
    def usd_additional(self):
        return self.usd_unit_price * self.total_purchase_qty

    @hybrid_property
    def usd_total(self):
        return self.usd_unit_price * self.total_demand_qty

    @hybrid_property
    def demand_function_list(self):
        return [i.function for i in self._budget_demand_list]

    # TODO: 需要校驗user_dept
    @validates('user_dept')
    def validate_user_dept(self, key, value):
        return value

    # TODO: 需要校驗user_dri
    @validates('user_dri')
    def validate_user_dri(self, key, value):
        return value

    # TODO: 需要校驗user_dept_manager
    @validates('user_dept_manager')
    def validate_user_dept_manager(self, key, value):
        return value

    # TODO: 需要校驗unit_price_currency
    @validates('unit_price_currency')
    def validate_unit_price_currency(self, key, value):
        return value

    # TODO: 需要校驗buyer
    @validates('buyer')
    def validate_buyer(self, key, value):
        return value

    # TODO: 需要校驗addition
    @validates('addition')
    def validate_addition(self, key, value):
        return value


    def _forbidden_cross_function_modify(self):
        # TODO: 需要校驗非通用物料跨function修改預算詳情
        #     if self.partnumber_station_mapping_name is not "ALL" and this partnumber's station entity function attr not match current user function:
        #         raise ForbiddenError(msg=f'budget content can not be modified while locked status')
        if enum_role.LL in [_role.role_name for _role in current_user._roles]:
            return
        if not any(_func in self.demand_function_list for _func in current_user._functions):
            raise ForbiddenError(msg=f'budget content can not be modified while function of user not in demand list')

    def _budget_content_lock(self):
        _budget = Budget.get_model_by_id(self.budget_id)
        if _budget.is_lock:
            raise ForbiddenError(msg=f'budget content can not be modified while locked status')


@event.listens_for(BudgetContent, 'before_update')
def budget_content_before_update_handler(mapper, connection, target: BudgetContent):
    target._budget_content_lock()
    target._forbidden_cross_function_modify()


@event.listens_for(BudgetContent, 'before_insert')
def budget_content_before_insert_handler(mapper, connection, target: BudgetContent):
    target._budget_content_lock()


@event.listens_for(BudgetContent, 'before_delete')
def budget_content_before_delete_handler(mapper, connection, target: BudgetContent):
    target._budget_content_lock()
    target._forbidden_cross_function_modify()
