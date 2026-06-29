import functools
import threading
import time


class DebugTracker:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
        self.max_events = 200
        self.enabled = True

    def log_event(self, event_type, details, stack_info=False):
        if not self.enabled:
            return

        with self.lock:
            timestamp = time.time()
            event = {
                "timestamp": timestamp,
                "type": event_type,
                "details": details,
                "thread": threading.current_thread().name,
            }

            if stack_info:
                import traceback

                event["stack"] = traceback.format_stack()

            self.events.append(event)
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events :]

            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{time_str}.{int((timestamp % 1) * 1000):03d}] {event_type}: {details}")

            if stack_info and "stack" in event:
                print("  Stack trace (last 3):")
                for line in event["stack"][-3:]:
                    print(f"    {line.strip()}")

    def dump_recent_events(self, last_n=30):
        with self.lock:
            print("\n" + "=" * 50)
            print("ULTIMOS EVENTOS DE DEBUG")
            print("=" * 50)
            for event in self.events[-last_n:]:
                time_str = time.strftime("%H:%M:%S", time.localtime(event["timestamp"]))
                print(f"[{time_str}] {event['type']}: {event['details']}")
            print("=" * 50 + "\n")


debug = DebugTracker()


def debug_method(method_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            debug.log_event(f"{method_name}_START", f"Args: {len(args)}")
            try:
                result = func(self, *args, **kwargs)
                debug.log_event(f"{method_name}_END", "Success")
                return result
            except Exception as exc:
                debug.log_event(f"{method_name}_ERROR", f"Error: {exc}", stack_info=True)
                raise

        return wrapper

    return decorator

