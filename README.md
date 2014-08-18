# watchprocess

This is a process instrumentation tool which will collect data about a
running process and create a report.

## Workflow

There are three steps to collecting data. Add symlinks to monitored processes. Run processes via the symlinks. Collect logs and build report. 

### Select programs to be monitored

Add symlinks to watchprocess.py on you PATH. 

There are example symlinks in the test/symlinks subdirectory of this repository. 

### Run the process(es) to be monitored

Just like normal, the symlinks on the path will redirect. 

### Collect the data

Run `watchprocess collect` to generate a report

If you do not want to continue aggregating the logs run:

`watchprocess clean`

Which will remove all logs from the configured logging directory. 

### Configure Logging (Optional)

Set the logging directory for log file collection. This is optional the default will be /tmp/watchprocess

### Example workflow

```
cd WATCHPROCESS_CHECKOUT/test/symlinks && export PATH=:`pwd`:$PATH
make
WATCHPROCESS_CHECKOUT/watchprocess.py collect --csv
```

