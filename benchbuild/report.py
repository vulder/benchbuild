import os
from plumbum import cli
import benchbuild.reports as Reports
from benchbuild.settings import CFG


ReportRegistry = Reports.ReportRegistry


class BenchBuildReport(cli.Application):
    """Generate Reports from the benchbuild db."""

    def __init__(self, executable):
        super(BenchBuildReport, self).__init__(executable=executable)
        self.experiment_names = []
        self.experiment_ids = []
        self.outfile = "report.csv"

    @cli.switch(["-E", "--experiment"], str, list=True,
                help="Specify experiments to run")
    def experiments(self, experiments):
        self.experiment_names = experiments

    @cli.switch(["-e", "--experiment-id"], str, list=True,
                help="Specify an experiment id to run")
    def experiment_ids(self, ids):
        self.experiment_ids = ids

    @cli.switch(["-o", "--outfile"], str,
                help="Output file name")
    def outfile(self, outfile):
        self.outfile = outfile

    def main(self, *args):
        Reports.discover()
        reports = ReportRegistry.reports

        for exp_name in self.experiment_names:
            if exp_name not in reports:
                continue

            for report_cls in reports[exp_name]:
                print("Writing '{0}'".format(self.outfile))
                report = report_cls(self.experiment_ids, self.outfile)
                report.generate()
        exit(0)