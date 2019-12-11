import asyncio
import regex
import traceback
import sys
from async_socket_connection import *
from helper import *


class CiscoSyncObject():
	cisco_async_object = None
	loop = None
	def __init__(self,ip):
		'''__init__
		
		The Constructor will simply set an instance variable of an instance of the CiscoAsyncObject inside of async_socket_connection.py. The constructor runs the Asyncio Loop that will never end. 
		
		Arguments:
			ip {string} -- ip address of device to access
		
		Returns:
			nothing -- nothing
		'''
		async def instantiate_inner_func(loop,ip): 
			cisco_async_object = CiscoAsyncObject()
			await cisco_async_object.async_cisco_socket(loop,ip)
			return cisco_async_object
		self.loop = asyncio.new_event_loop()
		asyncio.set_event_loop(self.loop)
		tasks = [asyncio.ensure_future(instantiate_inner_func(self.loop,ip))]
		nodes = self.loop.run_until_complete(asyncio.gather(*tasks))
		object = l(nodes,0)
		self.cisco_async_object = object
	def __getattr__(self,name,*args,**kwargs):
		'''__get_attr
		
		__getattr__ and __call__ are the two methods that are called when an unknown function is ran in a Python Class, similar to the behavior to the PHP __get magic function. Here the method call is saved for later use in the __call__ function. GetAttr dunder method gets the function name.
		
		Arguments:
			name {string} -- method name
			*args {[type]} -- [description]
			**kwargs {[type]} -- [description]
		
		Returns:
			CiscoSyncSocket -- Self
		'''
		self.method_call = name
		return self
	def __call__(self,name=None,*args,**kwargs):
		'''__call__
		
		See the getattr method. __getattr__ and __call__ both deal with unknown functions. But there's a lot more. getattr(self.cisco_async_object,self.method_call)(name,*args,**kwargs) calls the function dynamically. It calls the self.method call (by call) on the self.cisco_async_object. 
		
		Arguments:
			name {string} -- argument inside of function
			*args {[type]} -- [description]
			**kwargs {[type]} -- [description]
		
		Returns:
			string -- result
		'''
		return l(self.loop.run_until_complete(asyncio.gather(getattr(self.cisco_async_object,self.method_call)(name,*args,**kwargs))),0)


