import sys
from operator import itemgetter, attrgetter
import logging

from lxcp.lib import Lib
from lxcp.model import *
from lxcp import app

logger = logging.getLogger(__name__)

def host_schedule(host):
    """Schedule a new slot on a host

    This function is called periodically (once per slot time unit, e.g. once
    per hour) and schedules containers based on a "least run slots first" basis.

    The algorithm simply tries to fill up the host capacity, picking jobs that
    have the least elapsed runtime first.

    Note: This advantages newly requested slots over old ones.
    """
    containers = host.containers
    pending_slots = [slot for slot in host.slots if slot.hours > slot.hours_used]

    pending_slots.sort(key=attrgetter('hours_used'))

    schedule_containers = {}
    ram_sum = 0
    cpu_sum = 0
    for slot in pending_slots:
        if slot.container in schedule_containers:
            logger.info('Trying to schedule {} twice, in slot {} (already schedule in {})'.format(slot.container, slot, schedule_containers[slot.container]))
            continue
        if ram_sum + slot.nram > host.nram:
            continue
        if cpu_sum + slot.ncpu > host.ncpu:
            continue
        schedule_containers[slot.container] = slot
        slot.hours_used = slot.hours_used + 1
        slot.save()
        ram_sum = ram_sum + slot.nram
        cpu_sum = cpu_sum + slot.ncpu

    for container in containers:
        if container in schedule_containers:
            logger.info('Scheduling slot {}'.format(schedule_containers[container]))
            lxc_cont = container.lxc()
            lxc_cont.config.update({
                'limits.cpu': str(slot.ncpu),
                'limits.memory': str(slot.nram) + 'GB',
                'limits.cpu.priority': '10' # Scheduled containers get high priority
                })
            lxc_cont.save()
            container.schedule()
        else:
            lxc_cont = container.lxc()
            # Only unschedule if it was scheduled, i.e. got high priority
            if lxc_cont.config.get('limits.cpu.priority') == '10':
                lxc_cont.config.update({
                    'limits.cpu.priority': '0'
                    })
                lxc_cont.save()
                container.unschedule()

def cont_schedule():
    with app.app_context():
        lib = Lib.get_lib()

        hosts = Host.query.all()

        for host in hosts:
            host_schedule(host)
