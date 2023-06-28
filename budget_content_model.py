from sqlalchemy.ext.hybrid import hybrid_property

from sqlalchemy import UniqueConstraint, event
from sqlalchemy.orm import validates, backref

from app import db
from app.model import createAndUpdateMixin, base_model
from app.model.budget_model import Budget
from app.util.Api_exceptions import UnprocessableContentError
from app.util.enums import enum_addition_type, enum_buyer_type, enum_yes_no, enum_yes_none


class BudgetContent(db.Model, createAndUpdateMixin, base_model):
    __tablename__ = 'wms_budget_content'
    __table_args__ = (
        UniqueConstraint("partnumber_id", "budget_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    partnumber_id = db.Column(db.ForeignKey("wms_partnumber.id", ondelete="CASCADE"), nullable=False)
    budget_id = db.Column(db.ForeignKey("wms_budget.id", ondelete="CASCADE"), nullable=False)
    part_no = db.Column(db.String(24), nullable=False, default="料號新建中")
    addition = db.Column(db.Enum(enum_addition_type), nullable=True)
    lead_time_weeks_low = db.Column(db.Integer, nullable=True)
    lead_time_weeks_high = db.Column(db.Integer, nullable=True)
    buyer = db.Column(db.Enum(enum_buyer_type), nullable=True)
    # TODO: to be validated
    user_dri = db.Column(db.String(16), nullable=True)
    # TODO: to be validated
    user_dept = db.Column(db.String(32), nullable=True)
    # TODO: to be validated
    user_dept_manager = db.Column(db.String(16), nullable=True)
    apple_counterpart = db.Column(db.String(64), nullable=True)
    reimburse_customer_check = db.Column(db.Enum(enum_yes_none), nullable=True, default=True)
    emergency_purchase_submit = db.Column(db.Enum(enum_yes_no), nullable=True, default=True)
    purchase_reason = db.Column(db.String(512), nullable=True)
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

    # @hybrid_property
    # def user_code(self):
    #     # TODO: implement in DTO
    #     pass
    #
    # @hybrid_property
    # def spec(self):
    #     # TODO: implement in DTO
    #     pass
    #
    # @hybrid_property
    # def with_small_line_name(self):
    #     # TODO: implement in DTO
    #     pass

    @hybrid_property
    def reply_status(self):
        if self.addition is not None\
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
        self.usd_unit_price * self.total_purchase_qty
        return

    @hybrid_property
    def usd_total(self):
        return self.usd_unit_price * self.total_demand_qty



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


    # TODO: cross function modify forbidden
    def _forbidden_cross_function_modify(self):
        return


    def _budget_content_lock(self):
        _budget = Budget.get_model_by_id(self.budget_id)
        if _budget.is_lock:
            raise UnprocessableContentError(msg=f'budget content can not be modified while locked status')



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

