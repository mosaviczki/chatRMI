from Pyro4 import Daemon, Proxy, expose, oneway, callback, locateNS
from serpent import tobytes
from datetime import datetime
from hashlib import md5
from os import mkdir, remove
import threading

daemon = Daemon()

@expose
class Usuario():

    def __init__(self, nome, senha) -> None:
        self.nome = nome
        self.senha = senha
        self.mensagens = set()
        self.uri = None
        self.adm = False

    def set_adm(self, adm):
        self.adm = adm

    def set_uri(self, uri):
        self.uri = uri
    def update_mensagens(self, mensagens):
        self.mensagens = mensagens

    def get_nome(self):
        return self.nome

    def get_uri(self):
        return self.uri
    
    def get_mensagens(self):
        return self.mensagens

    def get_adm(self):
        return self.adm
    
    def hello(self):
        return "hello"

@expose
class Grupo():
    def __init__(self, nome):
        self.nome = nome
        self.uri = None
        self.adm = None
        self.membros = set()
        self.dir = None

    def set_membros(self, user):
        self.membros.add(user)

    def update_membros(self, membros):
        self.membros = membros

    def set_uri(self, uri):
        self.uri = uri

    def set_adm(self, user):
        self.adm = user

    def set_dir(self, dir):
        self.dir = dir

    def get_nome(self):
        return self.nome
        
    def get_dir(self):
        return self.dir

    def get_adm(self):
        return self.adm

    def get_membros(self):
        return self.membros
    
  
def carregarUsuarios():
    try:
        with open('users.dat', 'r') as file:
            
            if len(file.read()) == 0: #Não ha nada no arquivo
                return list()
        
            file.seek(0)
    
            list_user = []


            for user in file.readlines():
                user = user.split(':')
                nome = user[0]
                senha = user[1].split('|')[0]

                usuario = Usuario(nome, senha)
                
                msgs = user[1].split('|')[1:]
                for msg in msgs:
                    if msg != '\n':
                        msg = msg.replace('\n', '')
                        usuario.mensagens.add(msg)
            
                ns = locateNS()

                uri = daemon.register(usuario)
                usuario.set_uri(uri)
                
                ns.register(usuario.nome, uri)

                try:
                    mkdir('./' + usuario.nome)
                except:
                    pass
                list_user.append(usuario)
            
            return list_user
    except FileNotFoundError:
        return list()

def carregarGrupo():
    try:
        with open('groups.dat', 'r') as file:
            
            if len(file.read()) == 0: #Não ha nada no arquivo
                return list()
        
            file.seek(0)
    
            list_groups = []


            for group in file.readlines():
                group_list = group.split('|')

                nome = group_list[0]
                diretorio = group_list[1]
                adm = group_list[2]
                membros = group_list[3:]
                

                grupo = Grupo(nome)
                grupo.set_adm(adm)
                grupo.set_dir(diretorio)
                for user in membros:
                    user = user.replace('\n', '')
                    grupo.set_membros(user)
                
                ns = locateNS()

                uri = daemon.register(grupo)
                grupo.set_uri(uri)
                
                ns.register(grupo.nome, uri)


                list_groups.append(grupo)
            
            return list_groups

    except FileNotFoundError:
        return list()

@expose
class Servidor(object):
    
    usuarios = carregarUsuarios()
    grupos = carregarGrupo()

    def cadastrar_usuario(self, nome, senha):
        ns = locateNS()

        usuario = Usuario(nome, senha)
        uri = daemon.register(usuario)
        usuario.set_uri(uri)
        
        ns.register(nome, uri)
        
        try:
            with open('users.dat', 'r') as file:
                for linha in file.readlines():
                    if linha.split(':')[0] == nome:
                        return False
        except FileNotFoundError:
            pass
        with open('users.dat', 'a') as file:
            file.write(nome + ':' + senha + '\n')
        Servidor.usuarios.append(usuario)

        print(f"[+] Usuario {nome} criado")
    
    def show_users(self, users = usuarios):
        print('--------------------USERS-----------------------')
        for user in users:
            print("Nome:", user.nome)
            print("Senha:", user.senha)
            print("Msg:", user.mensagens)
            print("URI:", user.uri)
            print('-----------------------------------------------')
    
    def mandarMensagem(self, callback, id_rec, msg):
        
        cliente = Proxy(callback)
        usuario_manda = self.procuraUsuario(cliente.get_nome())

        horario = datetime.now()
        horario_str = horario.strftime('%d/%m/%Y %H:%M')


        for grupo in self.grupos:
            if grupo.nome == id_rec:

                print(grupo.get_membros())

                if ( usuario_manda.nome in grupo.get_membros() ) or (usuario_manda.nome == grupo.get_adm()):
                    with open(grupo.get_dir(), 'a') as file:
                        file.write(horario_str + '|' + usuario_manda.nome + '|' + msg + '\n')
                    return None
                else:
                    cliente.notificar('Voce nao e membro do grupo')
                    return None

        usuario_rec = self.procuraUsuario(id_rec)

        #Verifica se rec existe

        if usuario_rec == None:
            cliente.notificar('Usuario não existe!')
            return None

        aux = list()
        aux.append(str(usuario_manda.nome))
        aux.append(str(usuario_rec.nome))
        aux.sort()

        arq_nome = aux[0] + aux[1]
        arq_nome = md5(arq_nome.encode())
        arq_nome = arq_nome.hexdigest()
        arq_nome = arq_nome + '.log'

        if self.vrfHash(usuario_manda.nome, arq_nome):
            with open(arq_nome, 'a') as file:
                file.write(horario_str + '|' + usuario_manda.nome + '|' + msg + '\n')

        else:
            usuario_manda.mensagens.add(arq_nome)
            usuario_rec.mensagens.add(arq_nome)

            for user in aux:
                
                file = open('users.dat', 'r')
                lines = file.readlines()
                i = 0
                for itens in lines:
                    if itens.split(':')[0] == user:
                        linhas = i
                        texto = itens

                    i+=1
                file.close()

                lines[linhas] = texto.replace('\n', '') + '|' + arq_nome +'\n'

                file = open('users.dat', 'w')
                file.writelines(lines)
                file.close()
            with open(arq_nome, 'w') as file:
                file.write(horario_str + '|' + usuario_manda.nome + '|' + msg + '\n')

    def criaGrupo(self, callback, ids_part, nome_grupo):
        
        cliente = Proxy(callback)
        grupo = Grupo(nome_grupo)

        for user in ids_part:
            user = self.procuraUsuario(user)
            grupo.set_membros(user.get_nome())
        
        adm = self.procuraUsuario(cliente.get_nome())

        grupo.set_adm(adm.get_nome())

        horario = datetime.now()
        horario_str = horario.strftime('%d/%m/%Y %H:%M')

        hash_grupo = md5((nome_grupo+horario_str).encode())
        hash_grupo = hash_grupo.hexdigest()
        hash_grupo = hash_grupo + '.log'

        arq = open(hash_grupo, 'w')
        arq.close()

        grupo.set_dir(hash_grupo)

        
        with open('groups.dat', 'a') as file:
            file.write(grupo.nome + '|' + hash_grupo + '|' + adm.get_nome())
            self.addHash(adm.get_nome(), hash_grupo)
            for user in ids_part:
                user = self.procuraUsuario(user)
                file.write('|' + user.get_nome())
                self.addHash(user.get_nome(), hash_grupo)
            file.write('\n')

        Servidor.grupos.append(grupo)

    def addNovoUsuarioGrupo(self, callback, nome_grupo):
        cliente = Proxy(callback)
        grupo = self.procuraGrupo(nome_grupo)

        if grupo.get_adm() != cliente.get_nome():

            usuario = self.procuraUsuario(cliente.get_nome())
            grupo = self.procuraGrupo(nome_grupo)

            grupo.set_membros(usuario.get_nome())

            #if usuario.get_adm():
            file = open('groups.dat', 'r')
            lines = file.readlines()
            i = 0
            for itens in lines:
                if itens.split('|')[0] == nome_grupo:
                    linhas = i
                    texto = itens

                i+=1
                file.close()

                lines[linhas] = texto.replace('\n', '') + '|' + usuario.get_nome() +'\n'

                file = open('groups.dat', 'w')
                file.writelines(lines)
                file.close()

                #agora iremos adicionar a conversa ao Hash do cliente
                self.addHash(usuario.get_nome(), grupo.get_dir())

            #else:
                #cliente.notificar('Apenas o administrador pode inserir mebors no grupo')
        else:
            cliente.notificar('Não Executado, você é adm do grupo')
        
    def addHash(self, userName, hash_mensagem):
        file = open('users.dat', 'r')
        lines = file.readlines()
        i = 0
        for itens in lines:
            if itens.split(':')[0] == userName:
                linhas = i
                texto = itens

            i+=1
        file.close()

        lines[linhas] = texto.replace('\n', '') + '|' + hash_mensagem +'\n'

        file = open('users.dat', 'w')
        file.writelines(lines)
        file.close()
                
    def vrfHash(self, id, hsh_recebido):  
        with open('users.dat', 'r') as file:
            for linha in file.readlines():
                if linha.split(':')[0] == id:
                    linha = linha.split('|')[1:]
                    for hsh in linha:
                        if hsh.replace('\n','') == hsh_recebido:
                            return True

        return False

    def procuraUsuario(self, id, users = usuarios):
        for user in users:
            if id == user.nome:
                return user
        return None

    def excluirUsuario(self, id, nome_grupo):

        grupo = self.procuraGrupo(nome_grupo)
        membros = grupo.get_membros() 
   
        if id in membros:
            membros.remove(id)
            grupo.update_membros(membros)
            
        #exclui usuário do grupo
        file = open('groups.dat', 'r')
        lines = file.readlines()
        i = 0
        for itens in lines:
            if itens.split('|')[0] == nome_grupo:
                linhas = i
                texto = itens

            i+=1
        
        file.close()

        lines[linhas] = texto.replace('|'+id, '')

        file = open('groups.dat', 'w')
        file.writelines(lines)
        file.close()
              
        self.removeHash(id, grupo.get_dir())

    def removeHash(self, id, nomeHash):    
        texto = None

        usuario = self.procuraUsuario(id)
        conversas = usuario.get_mensagens()

        if nomeHash in conversas:
            conversas.remove(nomeHash)
            usuario.update_mensagens(conversas)
        
        file = open('users.dat', 'r')
        lines = file.readlines()
        i = 0
        for itens in lines:
            if itens.split(':')[0] == id:
                linhas = i
                texto = itens

            i+=1

        file.close()

        lines[linhas] = texto.replace('|' + nomeHash, '')

        file = open('users.dat', 'w')
        file.writelines(lines)
        file.close()


    def excluirGrupo(self, callback, nome_grupo):
        
        cliente = Proxy(callback)

        grupo = self.procuraGrupo(nome_grupo)

        if grupo == None:
            cliente.notificar('O Grupo não existe')
            return None

        if grupo.get_adm() == cliente.get_nome():

            for membro in grupo.get_membros():
                print(membro)
                
                file = open('users.dat', 'r')
                lines = file.readlines()
                i = 0
                for itens in lines:
                    if itens.split(':')[0] == membro:
                        linhas = i
                        texto = itens

                    i+=1

                file.close()

                lines[linhas] = texto.replace('|' + grupo.get_dir(), '')

                file = open('users.dat', 'w')
                file.writelines(lines)
                file.close()

            print(grupo.get_adm())
            file = open('users.dat', 'r')
            lines = file.readlines()
            i = 0
            for itens in lines:
                if itens.split(':')[0] == grupo.get_adm():
                    linhas = i
                    texto = itens

                i+=1

            file.close()

            lines[linhas] = texto.replace('|' + grupo.get_dir(), '')

            file = open('users.dat', 'w')
            file.writelines(lines)
            file.close()


            print('antes de abrir o arquivo')
            file = open('groups.dat', 'r')
            lines = file.readlines()
            j = 0
            print('anter do for itens')
            for itens in lines:
                if itens.split('|')[0] == nome_grupo:
                    linha = j
                j+=1

            file.close()

            print(lines)

            lines.pop(linha)

            print(lines)

            file = open('groups.dat', 'w')
            file.writelines(lines)
            file.close()

            remove(grupo.get_dir())

            self.grupos.remove(grupo)
            
        else:
            cliente.notificar('Apenas o ADM pode apagar o grupo')
        

    def procuraGrupo(self, nome_grupo):
        for grupo in self.grupos:
            if nome_grupo == grupo.get_nome():
                return grupo
        return None

    def login(self, callback, users = usuarios):

        cliente = Proxy(callback)

        nome = cliente.get_nome()
        senha = cliente.get_senha()
        
        for user in users:
            user.senha = user.senha.replace('\n', '')

            if nome == user.nome and senha == user.senha:
                cliente.notificar("Logging...")
                cliente.set_uriUser(user.uri)
        
    def carregarMensagens(self, arq_nome):
        file = open(arq_nome, 'r')
        lines = file.readlines()
        return lines

    def enviarArquivo(self, callback, nome, buffer):      
        cliente = Proxy(callback)

        buffer = tobytes(buffer)

        arq = open('./'+ cliente.get_nome() + '/' + nome, 'wb')
        arq.write(buffer)
        arq.close()

        cliente.notificar('Arquivo enviado com sucesso!')

    def showGrupos(self):
        for grupo in self.grupos:
            print(grupo.get_nome())
            print(grupo.get_dir()) 
            print(grupo.get_adm())
            print(grupo.get_membros())
            print() 
    
    def showUser(self):
        list_Usuarios = []

        for user in self.usuarios:
            list_Usuarios.append(user.get_nome())
        return list_Usuarios

    def meusGrupos(self, callback):
        cliente = Proxy(callback)
        usuario = self.procuraUsuario(cliente.get_nome())

        lista = []

        for grupo in self.grupos:
            if grupo.get_dir() in usuario.get_mensagens():
                lista.append(grupo.get_nome() + ':' + grupo.get_dir())

        return lista

    def sairGrupo(self, callback, nome_grupo):
        cliente = Proxy(callback)
        usuario = self.procuraUsuario(cliente.get_nome())
        grupo = self.procuraGrupo(nome_grupo)

        self.printGrupo(grupo)

        if usuario.get_nome() == grupo.get_adm():   #Cliente é o adm
            
            file = open('groups.dat', 'r')

            log = file.readlines()
            line = None
            n_line = None

            for n_line, x in enumerate(log):
                if grupo.get_nome() in x:
                    line = x
                    break

            line = line.split('|')

            if len(line) == 3: # Só existe o adm no grupo
                self.excluirGrupo(callback, nome_grupo)

            else:   #Existe mais pessoas no grupo doq so o ADM
                ################## CACHE ##################
                line[len(line) -1] = line[len(line) -1].replace('\n', '')   #Removendo \n do ultimo usuario

                grupo.set_adm(
                    line[(line.index(usuario.get_nome()) + 1)]  #Set como ADM o nome posterior o do antigo adm no 'groups.dat'
                )
                
                (grupo.get_membros()).remove(grupo.get_adm())   #Tirando o novo ADM dos membros

                ################## FILE ##################
                line.remove(usuario.get_nome())
                new_line = ('|'.join(str(x) for x in line) ) + '\n'

                self._atualizaLog('groups.dat', n_line, new_line)
    

                self.printGrupo(grupo)

        else:   #Cliente não é o adm
            pass

    def printGrupo(self, grupo):
        print(grupo.get_nome())
        print(grupo.get_dir()) 
        print(grupo.get_adm())
        print(grupo.get_membros())
        print('=========================') 
    
    def _atualizaLog(self, arq_nome, linha, string):
        with open(arq_nome, 'r') as file:
            linhas = file.readlines()
            linhas[linha] = string

            arq = open(arq_nome, 'w')
            arq.writelines(linhas)
            arq.close()


print("[+] Starting server")
ns = locateNS()
server = Servidor()
uri = daemon.register(server)
ns.register("RMI", uri)

print(uri)

daemon.requestLoop()
    