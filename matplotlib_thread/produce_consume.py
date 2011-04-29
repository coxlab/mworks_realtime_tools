#!/usr/bin/env python

#Let us profile code which uses threads
import thread
import time
from threading import *

class itemQ:

    def __init__(self):
        self.count=0

    def produce(self,num=1):
        self.count+=num

    def consume(self):
        if self.count: self.count-=1

    def isEmpty(self):
        return not self.count


class Producer(Thread):

    def __init__(self,condition,itemq,sleeptime=1):
        Thread.__init__(self)
        self.cond=condition
        self.itemq=itemq
        self.sleeptime=sleeptime

    def run(self):
        cond=self.cond
        itemq=self.itemq

        while 1 :
            
            cond.acquire() #acquire the lock
            print currentThread(),"Produced One Item"
            itemq.produce()
            cond.notifyAll()
            cond.release()

            time.sleep(self.sleeptime)


class Consumer(Thread):

    def __init__(self,condition,itemq,sleeptime=2):
        Thread.__init__(self)
        self.cond=condition
        self.itemq=itemq
        self.sleeptime=sleeptime

    def run(self):
        cond=self.cond
        itemq=self.itemq

        while 1:
            time.sleep(self.sleeptime)
            
            cond.acquire() #acquire the lock
            
            while itemq.isEmpty():
                cond.wait()
                
            itemq.consume()
            print currentThread(),"Consumed One Item"
            cond.release()
        
        

        
if __name__=="__main__":

    q=itemQ()

    cond=Condition()

    pro=Producer(cond,q)
    cons1=Consumer(cond,q)
    cons2=Consumer(cond,q)

    pro.start()
    cons1.start()
    cons2.start()
    while 1: pass

