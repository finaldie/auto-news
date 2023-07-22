

class OpsCounter:
    def __init__(self, name):
        self.name = name
        self.value = 0

    def get(self):
        return self.value

    def inc(self, delta):
        self.value += delta
        return self

    def set(self, val):
        self.value = val
        return self


class OpsStats:
    def __init__(self, name, sub_name):
        self.name = name
        self.sub_name = sub_name

        # counters (-1 means unknown/unset)
        self.stats_map = {
            "total_input": OpsCounter("total_input"),
            "post_deduping": OpsCounter("post_deduping"),
            "post_scoring": OpsCounter("post_scoring"),
            "post_filtering": OpsCounter("post_filtering"),
            "post_summary": OpsCounter("post_summary"),
            "post_ranking": OpsCounter("post_ranking"),
            "total_pushed": OpsCounter("total_pushed"),
        }

    def getCounter(self, name):
        """
        Counter name, e.g. total_input, post_deduping, etc
        """
        return self.stats_map.get(name)

    def print(self):
        print(f"{self.name}:")

        if self.sub_name:
            print(f" {self.sub_name}")

        for key, stat in self.stats_map.items():
            print(f" - {key}: {stat.get()}")
