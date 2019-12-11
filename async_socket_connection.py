import asyncio
import regex
import traceback
import sys
import time
from helper import *
class CiscoAsyncObject(object):
	command_timeout = 40
	def byte_to_string(self,obj):
		'''byte_to_string
		clean up a raw byte stream by recv. Chiefly used in read function.
		Arguments:
			obj {bytes (recv(1024))} -- messy bytes
		Returns:
			string -- so beautifully neat
		'''
		text = obj.decode('utf-8','ignore')
		text = ''.join([x for x in str(text) if ord(x) < 128])
		return text
	async def async_cisco_socket(self,loop,ip,port =23):
		'''async_cisco_socket
		
		This should be like the __init__ function of a socket class, but I don't know how to do init in an asynchronous context. So the end result will be that this will just populate self.reader & self.writer of this object
		'''
		connect_retries = 8
		tries = 0
		#try this the amount of connect_retries times
		while tries < connect_retries:
			try :
				reader, writer = await asyncio.open_connection(ip, port, loop=loop)
				if(reader is not None):
					hostname_line(ip,'Socket Created')
					#when the connection begins and you have to write "en" & password for Socket
					self.ip = ip
					self.hostname = get_hostname(ip)
					self.reader = reader
					self.writer = writer
					await self.initialize_socket()
					break
				else:
					print(reader,writer)
			except ConnectionRefusedError:
				tries = tries + 1
				hostname_line(ip,"Couldn't connect because of ConnectionRefusedError")
			except TimeoutError:
				tries = tries + 1
				hostname_line(ip,"Couldn't connect because of TimeoutError")
				await asyncio.sleep(1)
			except Exception as exc:
				tries = tries + 1
				hostname_line(ip,"Generic Exception -> %s" % (exc))
		if tries >= connect_retries:
			hostname_line(ip,"No socket connection because it exhausted it's maximum limit of retries.")
	async def sendline(self,command,**kwargs):
		'''sendline
		
		sendlines a command into the socket (Cisco here), and you could make it return the text to show up in the loop results, OR you could have it print as it goes. I prefer to have it print as it goes, and I did that option. 

		Kwargs is:

		expect = regex, which will break the recv read calls
		print = True/False, which prints the message as it goes
		newline = True/False (default True)
		'''
		chunks = []
		text = ''
		start_time_timeout_check = time.time()		
		reader = self.reader
		writer = self.writer
		ip = self.ip
		hostname = self.hostname
		print_it = kwargs.get('print',False)
		#expect regex that will break the recv loop
		expect_regex = kwargs.get('expect',None)
		default_regex = hostname + '.*' + '[#|\^|>]'
		#the default is in the right
		expect_regex = expect_regex if expect_regex != None else default_regex
		#IF NEWLINE KWARGS IS FALSE
		if kwargs.get("newline") is False:
			command = command
		else:
			command = command + "\n"
		#clear line
		for i in range(3):
			writer.write(b"\x15")
			await asyncio.sleep(.05)
		#do actual sending
		writer.write(command.encode())
		while 1:
			#Break up out of here no matte what, by the command timeout
			total_time = time.time() - start_time_timeout_check	
			# print("%s %s" % (command,total_time))
			if total_time > self.command_timeout:
				print('"%s" has timed out' % (command))
				return 'Time Out'
			try:
				chunk = await self.reader.read(8024)
				if not chunk:
					break
				chunk = self.byte_to_string(chunk)
				chunk_length = len(chunk)
				text = text + chunk
				# print("REGEX> ", expect_regex,  len(chunk), chunk.replace('\n', ' ').replace('\r', ' '),regex.search(expect_regex,chunk))
				#stop doing the recv at if the expect regex is not in the ENTIRE TEXT or the exception. It will stop at expect
				if regex.search(expect_regex,text) is not None:
					# print(command, "Expect happened")
					break
				
				
			except Exception as exc:
				print(hostname_line(ip, "Exception as %s" % (exc)))
				traceback.print_exc()
				await asyncio.sleep(.5)
				continue
			except:
				print("Error")
		#END READ
		#THIS IS DONE TO KEEP TRACK OF ? COMMANDS
		#This is for later text cleanup
		if len(command) > 0:
			self.current_command = command.strip()
		#just get the result without fluff
		#remove command in beginning & prompt at end
		text = text.replace(self.current_command,'')
		text = text.replace(self.current_command.replace(' ?',''),'')
		text = regex.sub(self.current_command,'',text)
		text = text.strip()
		#clean will remove the prompt, and other custom cleaning
		#remove the prompt in the end!
		text = regex.sub('\n%s.*[#|\^|>]' % (self.hostname),'',text)
		text = regex.sub('%s' % (self.current_command.replace(' ?','')),'',text)
		# text = text.strip()
		#clean up it for the console
		text = sanitize(text.replace('\n', ' ').replace("",'').strip())
		text = regex.sub('\r\s*','\r',text)
		#does the printing in each send line IF kwargs print is true (like print=True as parameter)
		if kwargs.get("newline") == True:
			header = wrap(wrap_hostname_line(ip,'Results of "%s"' % (command)))
			print(header + "\n" + text)
		return text

	async def initialize_socket(self):
		'''initialize_socket
		this is called by the async_connect to get to the config mode
		'''
		await self.sendline('en',expect="Password")
		await self.sendline('goon')
		await self.sendline('terminal length 0')
		await self.config_mode()
	async def config_mode(self):
		'''config mode
		Goes Into Config Mode of course
		'''
		await self.sendline("configure terminal")
	async def privileged_mode(self):
		'''privilged_mode
		the mode before global config mode, which is privileged mode
		'''
		await self.config_mode()
		await self.sendline("end")
	async def write(self,command):
		'''write
		
		Write raw BYTES

		command is in BYTES, not string
		'''
		# print("Writing: %s" % (command))
		self.writer.write(command)
	async def clear_line(self,command=b"\x15"):
		'''clear_line
		
		Simply writes b'\x15' into Telnet which clears the line! This is required for those ? help commands.
		This also represents Ctrl+U in the ASCII map, and is verified in Wireshark.
		'''
		await self.write(b"\x15")
