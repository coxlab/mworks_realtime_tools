#!/usr/bin/env python

import time

import physio_online

if __name__ == '__main__':
    cfg = physio_online.cfg.Config()
    cfg.read_user_config()

    data_source = physio_online.datasource.DataSource(cfg)

    while 1:
        data_source.update()
        time.sleep(.5)