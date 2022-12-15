from Pyro4 import Daemon, Proxy, expose, oneway, callback, locateNS
from hashlib import md5
import threading, time
@expose
class Cliente(object):
    def __init__(self, nome, senha):
        self.nome = nome
        self.senha = senha
        self.uri = None
        self.uriUser = None

    def get_nome(self):
        return self.nome

    def get_senha(self):
        return self.senha
    
    def get_uri(self):
        return self.uri

    def set_uriUser(self, uri):
        self.uriUser = uri

    def request_loop(self, daemon):
        daemon.requestLoop()
        time.sleep(2)
    @oneway
    def notificar(self, msg):
        print(msg)

    def show(self):
        print("Nome: ", self.nome)
        print("Senha: ", self.senha)
        print("Uri: ", self.uri)
        print("UriUSer: ", self.uriUser)

with Daemon() as daemon:
        
    with Proxy("PYRONAME:RMI") as server:

        cliente = None

        while True: 
            print("--------------------------------")
            print("1-Login\n2-Registrar\n3-Mandar mesagem\n4-Mostrar Cliente\n5-Carregar mensagens\n6-Enviar arquivo\n7-Criar Grupo")
            option = int(input(""))
            
            if option == 1:

                nome = input("Nome: ")
                senha = input("Senha: ")

                senha = md5(senha.encode())
                senha = senha.hexdigest()

                cliente = Cliente(nome, senha)

                callback = cliente
                callback.uri = daemon.register(callback)

                loop_thread = threading.Thread(target=callback.request_loop, args=(daemon, ))
                loop_thread.daemon = False
                loop_thread.start()

                server.login(callback.uri)

                if cliente.uriUser == None:
                    print('[-] Senha incorreta')
                    
                else:
                    print('[+] Logado!')

                    user = Proxy(cliente.uriUser)

                    cnv = user.get_mensagens()
                    print(cnv)
            
            if option == 2:

                nome = input("Digite seu nome: ")
                senha = input("Digite sua senha: ")

                senha = md5(senha.encode())
                senha = senha.hexdigest()   #Transformando em string 

                server.cadastrar_usuario(nome, senha)

            if option == 3:
                
                callback = cliente
                para = input("Digite para quem vai a msg: ")
                msg = input('Digite a msg: ')
                
                server.mandarMensagem(callback.uri, para, msg)

            if option  == 4:
                if cliente == None:
                    print("Cliente não logado!")
                else:
                    cliente.show()    

            if option == 5:       
                user = Proxy(cliente.uriUser)
                for arq in user.get_mensagens():
                    msgs = server.carregarMensagens(arq)
                    print(msgs)

            if option == 6:

                nomeFile = input("Nome do arquivo: ")

                arq = open(nomeFile, 'rb')

                arqNome = arq.name
                arqBuffer = arq.read()

                callback = cliente
                server.enviarArquivo(callback.uri, arqNome, arqBuffer)

            if option == 7:

                nome = input('Informe o nome do grupo: ')

                callback = cliente
                server.criaGrupo(callback.uri, ['Maycom', 'Luis'], nome)

            if option == 8:
                server.addNovoUsuarioGrupo(callback.uri, nome_grupo)
            

            if option == 9:
                server.show_users()