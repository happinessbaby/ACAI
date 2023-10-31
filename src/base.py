

# class BaseChat:


#     class __impl:
#         """ Implementation of the singleton interface """


#         def save_chat(self, chat):
#             self.chat = chat
#             print(self.chat)

#         def get_chat(self):
#             print(self.chat)
#             return self.chat
        
#         def save_entities(self, text):
#             self.entities = text

#         def get_entities(self):
#             return self.entities
        
#     __instance = None

#     def __init__(self):
#         """ Create singleton instance """
#         # Check whether we already have an instance
#         if BaseChat.__instance is None:
#             # Create and remember instance
#             BaseChat.__instance = BaseChat.__impl()

#         # Store instance reference as the only member in the handle
#         self.__dict__['_BaseChat__instance'] = BaseChat.__instance

#     def __getattr__(self, attr):
#         """ Delegate access to implementation """
#         return getattr(self.__instance, attr)

#     def __setattr__(self, attr, value):
#         """ Delegate access to implementation """
#         return setattr(self.__instance, attr, value)


        


    

    



    
    
    

