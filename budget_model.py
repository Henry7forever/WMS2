from sqlalchemy import UniqueConstraint, event
from sqlalchemy.orm import backref, validates

from app import db
from app.model import createAndUpdateMixin, base_model
from app.model.main_task_model import MainTask
from app.util.api_exceptions import UnprocessableContentError, ForbiddenError
from app.util.enums import enum_budget_type, enum_main_task_status_type


class Budget(db.Model, createAndUpdateMixin, base_model):
    __tablename__ = 'wms_budget'
    __table_args__ = (
        UniqueConstraint("name", "phase_id", "budget_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    phase_id = db.Column(db.ForeignKey("wms_phase.id", ondelete="CASCADE"), nullable=False)
    source_main_eq_task_id = db.Column(db.ForeignKey("wms_main_task.id", ondelete="CASCADE"))
    budget_type = db.Column(db.Enum(enum_budget_type), nullable=False)
    is_lock = db.Column(db.Boolean, nullable=False, default=False)
    pilot_budget_id = db.Column(db.ForeignKey("wms_budget.id", ondelete="CASCADE"))

    _budget_content_list = db.relationship("BudgetContent", cascade="all,delete")
    _source_main_eq_task = db.relationship("MainTask")
    # _phase = db.relationship("Phase", backref=backref("_budget_list", cascade="all,delete"))
    _phase = db.relationship("Phase")
    _pilot_budget = db.relationship("Budget", remote_side=[id],
                                    backref=backref("_extra_budget_list", cascade="all,delete"))


    def validate_source_main_eq_sub_tasks_all_approved(self):
        if self.source_main_eq_task_id is not None:
            _source_main_eq_task = MainTask.get_model_by_id(self.source_main_eq_task_id)
            if _source_main_eq_task.task_status == enum_main_task_status_type.STARTED:
                raise ForbiddenError(msg=f'sub tasks of source main eq_task must be all approved')


    def _validate_budget_type_and_source_main_eq_task_id_before_budget_insert(self):
        if self.budget_type == enum_budget_type.PILOT.value:
            if self.source_main_eq_task_id is None:
                raise UnprocessableContentError(msg=f'pilot budget must have source main eqlist task id')
        elif self.source_main_eq_task_id is not None:
            raise UnprocessableContentError(msg=f'source main eqlist task id of non pilot budget must be empty')


    def _validate_budget_type_and_pilot_budget_id_before_budget_insert(self):
        if self.budget_type == enum_budget_type.EXTRA.value:
            if self.pilot_budget_id is None:
                raise UnprocessableContentError(msg=f'extra budget must have parent pilot budget id')
        elif self.pilot_budget_id is not None:
            raise UnprocessableContentError(msg=f'binding pilot budget id of non extra budget must be empty')


    def _validate_budget_type_and_source_main_eq_task_id_when_budget_modify(self):
        if self.budget_type == enum_budget_type.PILOT:
            if self.source_main_eq_task_id is None:
                raise UnprocessableContentError(msg=f'pilot budget must have source main eqlist task id')
        elif self.source_main_eq_task_id is not None:
            raise UnprocessableContentError(msg=f'source main eqlist task id of non pilot budget must be empty')


    def _validate_budget_type_and_pilot_budget_id_when_budget_modify(self):
        if self.budget_type == enum_budget_type.EXTRA:
            if self.pilot_budget_id is None:
                raise UnprocessableContentError(msg=f'extra budget must have parent pilot budget id')
        elif self.pilot_budget_id is not None:
            raise UnprocessableContentError(msg=f'binding pilot budget id of non extra budget must be empty')



    def _validate_extra_pilot_binding_on_pilot_budget_before_budget_insert(self):
        if self.budget_type == enum_budget_type.EXTRA.value:
            _pilot_budget = Budget.get_model_by_id(self.pilot_budget_id)
            if _pilot_budget.is_lock:
                raise ForbiddenError(msg=f'extra budget can not bind on locked pilot budget')


    def _sync_extra_budget_is_lock_when_update(self, connection):
        if self.budget_type == enum_budget_type.PILOT:
            _extra_budget_list = Budget.get_model_list_by_params({"pilot_budget_id": self.id})
            for extra_budget in _extra_budget_list:
                connection.execute(
                    Budget.__table__.update().
                        where(Budget.__table__.c.id == extra_budget.id).
                        values(is_lock=self.is_lock))


@event.listens_for(Budget, 'before_update')
def budget_before_update_handler(mapper, connection, target: Budget):
    target._validate_budget_type_and_source_main_eq_task_id_when_budget_modify()
    target._validate_budget_type_and_pilot_budget_id_when_budget_modify()
    target._sync_extra_budget_is_lock_when_update(connection)

@event.listens_for(Budget, 'before_insert')
def budget_before_insert_handler(mapper, connection, target: Budget):
    target._validate_budget_type_and_source_main_eq_task_id_before_budget_insert()
    target._validate_budget_type_and_pilot_budget_id_before_budget_insert()
    target.validate_source_main_eq_sub_tasks_all_approved()
    target._validate_extra_pilot_binding_on_pilot_budget_before_budget_insert()

