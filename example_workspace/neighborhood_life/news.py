# Provides notifications at start/end of each block.
from sims4communitylib.utils.common_icon_utils import CommonIconUtils
from sims4communitylib.utils.common_notification_utils import CommonBasicNotification
from sims4communitylib.utils.sims.common_sim_name_utils import CommonSimNameUtils
from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from .schedules import TimeBlock
from .util import log

class NewsCenter:
    def __init__(self, cfg: 'NLConfig'):
        self.cfg = cfg

    def post_start(self, sim_info, block: TimeBlock):
        if not self.cfg.news_enabled:
            return
        name = CommonSimNameUtils.get_full_name(sim_info)
        text = f"{name} started: {block.action.replace('_', ' ').title()}"
        CommonBasicNotification("Neighborhood News", text, icon=CommonIconUtils.load_question_mark_icon()).show()

    def post_end(self, sim_info, block: TimeBlock):
        if not self.cfg.news_enabled:
            return
        name = CommonSimNameUtils.get_full_name(sim_info)
        text = f"{name} finished: {block.action.replace('_', ' ').title()}"
        CommonBasicNotification("Neighborhood News", text, icon=CommonIconUtils.load_question_mark_icon()).show()
