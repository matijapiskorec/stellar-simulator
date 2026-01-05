import logging
import sys
from io import StringIO

class Log:

    def __init__(self):

        self.verbosityDict = {0: False,
                              1: logging.CRITICAL,
                              2: logging.ERROR,
                              3: logging.WARNING,
                              4: logging.INFO,
                              5: logging.DEBUG}

        self.log_stream = StringIO()  # Memory stream for logs

        self.simulator = logging.getLogger('SIMULATOR')
        self.node = logging.getLogger('NODE')
        self.gillespie = logging.getLogger('GILLESPIE')
        self.event = logging.getLogger('EVENT')
        self.consensus = logging.getLogger('CONSENSUS')
        self.ledger = logging.getLogger('LEDGER')
        self.quorum = logging.getLogger('QUORUM')
        self.network = logging.getLogger('NETWORK')
        self.mempool = logging.getLogger('MEMPOOL')
        self.transaction = logging.getLogger('TRANSACTION')
        self.message = logging.getLogger('MESSAGE')
        self.value = logging.getLogger('VALUE')
        self.storage = logging.getLogger('STORAGE')
        self.test = logging.getLogger('TEST')

        self.log_format = '%(msecs).2f - %(name)s - %(levelname)s - %(message)s'

        # Stream handler for console output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(self.log_format))
        logging.basicConfig(handlers=[console_handler], format=self.log_format)

        # Memory handler to store logs in memory
        memory_handler = logging.StreamHandler(self.log_stream)
        memory_handler.setFormatter(logging.Formatter(self.log_format))

        for logger in [self.simulator, self.node, self.gillespie, self.event, self.consensus,
                       self.ledger, self.quorum, self.network, self.mempool, self.transaction,
                       self.message, self.value, self.storage, self.test]:
            logger.addHandler(memory_handler)

    def set_level(self, level):
        for logger in [self.simulator, self.node, self.gillespie, self.event, self.consensus,
                       self.ledger, self.quorum, self.network, self.mempool, self.transaction,
                       self.message, self.value, self.storage, self.test]:
            logger.setLevel(level)
        return

    def export_logs_to_txt(self, file_path):
        with open(file_path, 'w') as log_file:
            log_file.write(self.log_stream.getvalue())
        print(f"Logs exported to {file_path}")

log = Log()
