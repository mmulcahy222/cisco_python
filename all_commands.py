import regex
import time
from helper import *
from sync_socket_connection import *
from socket_connection import *

#########################
#    CLASS
#########################
class CiscoHelpCommands():
	tokens_return = ['<cr>','%','|','do']
	tokens_continue = ['bfd','gshut','exact-match', 'gshut', 'local-AS','no-advertise','no-export','remembered']
	replace_with_string = ['WORD','LINE']
	filename_destination = 'C:/makeshift/files/cisco_python/txt/all_commands.txt'
	current_command_description = ''
	past_command_tokens = []
	depth = 1
	letters_omit = ['a','b','c','d','e','f','g','h']

	def traverse_cisco_commands(self,command):
		try:
			#Leave if there's a duplicate. Avoids commands like "do show bgp * all community gshut gshut gshut gshut ?"
			try:
				command_split = command.split()
				if command_split[-1] == command_split[-2]:
					return
				if command_split[-1] == command_split[-3]:
					return
			except IndexError:
				pass
			command_question = command + " ?"
			#ACTUALLY run the command with ? to get the autocompleted results of prospective new commands. 
			#You WILL have to run s.write(b"\x15") because those bytes will clear up the line for future commands
			#Be sure to put in newline=False for ? help commands then s.write(b"\x15")
			command_question_response_raw = s.sendline(command_question,newline=False) 
			#This would put in Ctrl+U (verified by Wireshark).
			#NOTE: b"\15" is needed if you don't do another s.sendline("") underneath
			#Putting down s.write(b"\x15") is faster than another sendline beneath s.write(b"\x15")
			for i in range(3):
				s.write(b"\x15")
				time.sleep(.05)
			#Print
			command_response_dict = {}
			command_response_split = command_question_response_raw.split('\r')
			#iterate through the possible commands returned by ?
			#construct command_response_dict of keys & descriptions
			for line in command_response_split:
				try:
					line = line.strip().split()
					command_token = line[0].strip()
					command_description = ' '.join(line[1:])
					command_response_dict[command_token] = command_description
				except IndexError:
					pass
			command_tokens = list(command_response_dict.keys())
			first_command_token = l(command_tokens,0)
			#########################
			#    START PRINTING & SAVING
			#########################
			#Print the results of the ? command to show all possible new tokens IF there is an abundance of them (doesnt start with things like | or <cr>). If it starts with those tokens, don't print.
			separator = "\n" * 2
			text = ''
			if first_command_token not in self.tokens_return:
				text = wrap('Possible Commands from: "%s"' % (command_question))
				text += tab_lines(command_question_response_raw)
				text += separator
				print(text)
				file_append_contents(self.filename_destination,text)
			#RUN THE ACTUAL COMMAND ONLY IF THE CARRIAGE RETURN IS IN THE RETURNED RESULT
			if '<cr>' in command_question_response_raw:
				#get results from the command
				start_time = time.time()
				command_response_raw = s.sendline(command)
				total_time = round(time.time() - start_time, 5)
				text = wrap('Command: "%s"' % (command) + '\n#\tDescription: "%s"' % (self.current_command_description) + '\n#\tTime: %s seconds' % (total_time) + '\n#\tDepth: %s' % (self.depth))
				if len(command_response_raw.strip()) > 2:
					text += tab_lines(command_response_raw)
				else:
					text += "\n\tNone"
				text += separator
				print(text)
				file_append_contents(self.filename_destination,text)
			#########################
			#    END PRINTING & SAVING
			#########################
			#command_token: first word showing up in a ? command that is a part (token) of a full cisco command
			#command_description: the long-winded description that comes after a token
			#
			#"aaa            Show AAA values" 
			#command_token: aaa
			#command_description: Show AAA values
			#command 
			for command_token,command_description in command_response_dict.items():
				#ELIMINATE ALL THE VARIABLE COMMANDS WHERE multiple values are combined together for multiple permutations
				# print(command,self.past_command_tokens,command_tokens)
				if all(small_list_item in self.past_command_tokens for small_list_item in command_tokens) and self.past_command_tokens != command_tokens and len(command_tokens) > 1:
					return
				self.current_command_description = command_description
				self.past_command_tokens = command_tokens
				# print("Command Token: ", command_token)
				# print(new_command, command_question_response_raw,command_token,command_description)
				# A SWITCH CASE ON WHAT TO DO FOR CERTAIN COMMAND TOKENS (first word in the line) 
				# Pretty much CHANGE the command token to something else
				# 
				#If carriage is in the command description, you went as far as you could go. Leave recursion for it went as far as it could go
				if '<cr>' in command_description:
					return
				#do this while constructing the program, to skip over some commands
				#do this for debugging
				#letters omit list will run commands
				elif (self.depth == 1 and any([command_token.startswith(letter) for letter in self.letters_omit])):
					continue
				#Get rid of BGP commands like 'exact-match', 'gshut', 'local-AS','no-advertise','no-export' where different combinations of those words are permitted
				elif command_token in self.tokens_continue:
					continue
				# % means unrecognied command. This will leave recursion at this maximum depth
				elif command_token in self.tokens_return:
					return
				# REMOVE ASAP!!!!!!!!!!!!!!!!!!!!!!!!
				elif 'show ip' in command and len(command.split()) <= 4 and command_token <= 'otpf':
					continue
				#no single letter command tokens for "command: "do show event manager policy active class A B C D E F G H I J M W L"
				elif len(command_token) == 1 and command_token.isalpha():
					return
				#Gets out of "show glbp Ethernet 1/0 detail" which bogs down the damn program
				#eliminates "active brief client-cache detail disabled init listen standby |""
				elif 'groups in' in command_description.lower():
					return
				#no depth beyond 14
				elif self.depth >= 15:
					return
				#things like WORD & LINE
				elif command_token in self.replace_with_string:	
					command_token = 'GOONERY'
				elif 'A.B.C.D' in command_token or 'Hostname' in command_token:
					#IP address of socket object
					command_token = s.ip
				#put down the interface
				elif 'interface' in command_description.lower():
					command_token = '1/0'
				elif regex.search('<\d*-\d*>',command_token) is not None:
					command_token = 1

				new_command = command + ' ' + str(command_token)
				# print(new_command)
				self.depth += 1
				self.traverse_cisco_commands(new_command)
				self.depth -= 1
		except Exception as exc:
			file_append_contents(self.filename_destination,"%s" % (exc))
#########################
#    Client
#########################
chc = CiscoHelpCommands()
s = CiscoSyncObject("10.50.0.105")
chc.traverse_cisco_commands('do show onep')