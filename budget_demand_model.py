from sqlalchemy.ext.hybrid import hybrid_property

from sqlalchemy import UniqueConstraint, event
from sqlalchemy.orm import validates

from app import db
from app.model import createAndUpdateMixin, base_model
from app.model.budget_content_model import BudgetContent
from app.util.api_exceptions import ForbiddenError
from app.util.current_user import current_user
from app.util.enums import enum_role


class BudgetDemand(db.Model, createAndUpdateMixin, base_model):
    __tablename__ = 'wms_budget_demand'
    __table_args__ = (
        UniqueConstraint("function", "budget_content_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # TODO: to be validated
    function = db.Column(db.String(64), nullable=False)
    demand_qty = db.Column(db.Integer, nullable=False)
    budget_content_id = db.Column(db.ForeignKey("wms_budget_content.id", ondelete="CASCADE"), nullable=False)

    _budget_content = db.relationship("BudgetContent")

    @hybrid_property
    def usd_total(self):
        return self._budget_content.usd_unit_price * self.demand_qty


    # TODO: 需要校驗function
    @validates('function')
    def validate_function(self, key, value):
        return value

    # TODO: cross function modify forbidden
    def _forbidden_cross_function_modify(self):
        if enum_role.LL in [_role.role_name for _role in current_user._roles]:
            return
        if self.function not in current_user._functions:
            raise ForbiddenError(msg=f'budget demand can not be modified while function of user not match demand function')


    def _budget_demand_lock(self):
        _budget_content = BudgetContent.get_model_by_id(self.budget_content_id)
        if _budget_content._budget.is_lock:
            raise ForbiddenError(msg=f'budget demand can not be modified while locked status')


@event.listens_for(BudgetDemand, 'before_update')
def budget_demand_before_update_handler(mapper, connection, target: BudgetDemand):
    target._budget_demand_lock()
    target._forbidden_cross_function_modify()

@event.listens_for(BudgetDemand, 'before_insert')
def budget_demand_before_insert_handler(mapper, connection, target: BudgetDemand):
    target._budget_demand_lock()

@event.listens_for(BudgetDemand, 'before_delete')
def budget_demand_before_delete_handler(mapper, connection, target: BudgetDemand):
    target._budget_demand_lock()
    target._forbidden_cross_function_modify()