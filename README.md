# ct_tsm
This tool is used to implement a HSM solution on Lustre with a TSM based tape archive. 

This tool is using UUIDs to keep a unique reference between Lustre and TSM. This allow a file to be renamed and even the underlaying Lustre FS to be moved to a different FS without having to touch the TSM server.

A new file is assigned a UUID on the first archive command and is stored in the xattr of the file. This UUID will be reused on every archive request on that file, this will create multiple version of the file in TSM, they can be cleaned up to only keep a single copy.

## Requirements
* [lhsmtool_cmd from Robinhood](https://github.com/cea-hpc/robinhood/)
* [Python TSM API](https://github.com/bbrauns/tsm-api-client)
 * TSM API installed from IBM's RPM and configured to access the TSM server 
* Python >= 3.5
 * TSM API module
 *  `xattr` module

## Usage

This example is using a python virtualenv to run the correct Python version on Centos 7. Put the following configuration in `/etc/lhsm_cmd.conf`. 

```
[commands]
archive = /root/env/bin/python3.6 /root/ct_tsm.py --archive --fd={fd} --fid={fid} --lustre-root=/project
restore = /root/env/bin/python3.6 /root/ct_tsm.py --restore --fd={fd} --fid={fid} --lustre-root=/project
remove = /root/env/bin/python3.6 /root/ct_tsm.py --remove --fid={fid} --lustre-root=/project
```

Run `lhsmtool_cmd` and send HSM requests with the various `lfs hsm_*` commands.