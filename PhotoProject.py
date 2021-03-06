import face_recognition, os, sys, time, csv, pickle
from tqdm import tqdm
from PIL import Image
from shutil import copyfile
from multiprocessing import Process, Pool, cpu_count
    
# ---------------------------------------------------#
''' 
    Automatically saves any found face into a folder. 
    Naming convention is [x][photoID].jpg (ie 01138, 11138, 21138)
'''

def save_find_faces(filename, accessor="",accessor2="faces"):

    try:

        if type(filename)==str:
            filename = [filename]

        for z in filename:

            image = face_recognition.load_image_file(accessor+z)
            face_locations = face_recognition.face_locations(image,model='hog')
            y = face_recognition.face_encodings(image,face_locations)

            img = Image.open(accessor+z)
            counter = 0
            z = z.split('/')[-1]

            for x in face_locations:
                
                img2 = img.crop((x[3],x[0],x[1],x[2]))
                img2.save(accessor2+'/nonclustered/'+str(counter)+z)

                c = open(accessor2+'/meta/'+str(counter)+z+'.dat','wb')
                pickle.dump(y[counter],c)
                c.close()
                
                counter += 1

        return True

    except Exception as e: 
        print(e)
        print ("Found Error, Crash Error Code 100")
        return False
            
# ---------------------------------------------------#

def line_split(N, K=1):
    length = len(N)
    return [N[i*length/K:(i+1)*length/K] for i in range(K)]

# ---------------------------------------------------#

def save_find_faces_all(location_pictures = './pictures',location_meta='./faces/meta',accessor2='faces'):

    try:

        print ("")
        print ("== Detecting Faces in Images ==")
        print ("")

        pool, dat = [], []
        to_be_processed = (os.listdir(location_pictures))
        exists = [x[1:] for x in os.listdir(location_meta)]

        for x in to_be_processed:

            if x+'.dat' in exists or x == '.DS_Store':
                pass
            else:
                dat.append(x)

        chunked = line_split(dat,cpu_count()-1)

        for y in chunked:         
            p1 = Process(target=save_find_faces, args=(y,location_pictures,accessor2,))
            pool.append(p1)

        for y in pool:
            y.start()

        print ("Processing Started for "+ str(len(dat))+" pictures!")

        for y in pool:
            y.join()

        print ("Successfully Identified Faces")
        print ("")

    except Exception as e: 
        print(e)
        return False

# ---------------------------------------------------#

''' 
    Compare distance between two faces to see if its the same person. 
    .45 is optimal threshold (per face rec library, referencing CMU OpenFace algorithm)
    Below .45 means its the same person, and above means its not. 
'''
def compare_faces(face1,face2):
    try:
        try:
            my_face_encoding = pickle.load(open('./faces/meta/'+face1+'.dat','rb'))
        except:
            print ("Error Loading Image 1")
            return -1
        try:         
            unknown_face_encoding = pickle.load(open('./faces/meta/'+face2+'.dat','rb'))
        except:
            print ("Error Loading Image 2")
            return -1
            
        results = face_recognition.face_distance([my_face_encoding], unknown_face_encoding) 
        return results[0]
    except:
        print ("Found Error, Crash Error Code 102")
        return -1

# ---------------------------------------------------#

def compare_all_faces():
    try:
        # Initializing Variables and Data Types
        ifile  = open('facedata.csv', "wb")
        writer = csv.writer(ifile)
        data,names,badfiles = [],[],[]

        # Writing Initial Row to CSV
        writer.writerow(['Picture1','Picture2','Distance'])

        # Process all files in nonclustered
        available_files = os.listdir('./faces/meta/')

        print ("")
        print ("== Comparing Faces ==")
        print ("")
        print ("Encoding Faces")

        # Encoding all files to memory
        for x in tqdm(range(len(available_files))):
            try:
                data.append(pickle.load(open('./faces/meta/'+available_files[x],'rb')))
                names.append(available_files[x][:-4])
            except:
                badfiles.append(available_files[x][:-4])
        
        # Comparing the encoded files
        print ("Comparing Faces")
        for y in tqdm(range(len(data))):
            for z in range(y+1, len(data)):    
                try:
                    results = face_recognition.face_distance([data[y]], data[z]) 
                    writer.writerow([names[y],names[z],str(results[0])])
                except:
                    pass

    except:
        print ("Found Error, Crash Error Code 103")
        return -1

# ---------------------------------------------------#

def check_exist(branch,file1):
    for x in branch:
        if file1 in x:
            return True
    return False

# ---------------------------------------------------#

def check_existance(branch,to_search1,to_search2):
    for x in range(len(branch)):
        if to_search1 in branch[x] or to_search2 in branch[x]:
            return (x)
    return (-1)

# ---------------------------------------------------#

def cluster_faces(threshold=0.45):
    try:
        # Initializing Variables and Data Types
        ifile  = open('facedata.csv', "rb")
        writer = csv.reader(ifile)
        branch = []
        folder_id = 0

        # Iterating through CSV File
        for x in writer:
            try:
                if float(x[-1]) <= threshold:       # Evaluating Face Distance with Threshold
                    tag = check_existance(branch,x[0],x[1])   # Checking Existance in any pre-existing branch
                    if tag >= 0:
                        if x[0] in branch[tag]:
                            if check_exist(branch,x[1])==False:
                                branch[tag].append(x[1])
                        elif x[1] in branch[tag]:
                            if check_exist(branch,x[0])==False:
                                branch[tag].append(x[0])
                    else:
                        branch.append([x[0],x[1]])
            except:
                pass


        # Sorting Facial Images with Existing Branch Classifications
        for x in branch:
            if str(folder_id) in os.listdir("./faces/clustered/"):
                pass
            else:
                os.mkdir("./faces/clustered/"+str(folder_id))
            for y in x:
                copyfile("./faces/nonclustered/"+y, "./faces/clustered/"+str(folder_id)+"/"+y)
            folder_id += 1


        # Generating Branches for Independent Facial Images
        for y in os.listdir('./faces/nonclustered/'):
            if check_exist(branch,y)==False:
                if str(folder_id) not in os.listdir("./faces/clustered/"):
                    os.mkdir("./faces/clustered/"+str(folder_id))
                copyfile("./faces/nonclustered/"+y, "./faces/clustered/"+str(folder_id)+"/"+y)
                folder_id += 1
            
    except:
        print ("Found Error, Crash Error Code 104")
        return -1
    
# ---------------------------------------------------#

def eval_against_face(image,imageloc):

    # Initializing Variables and Data Types
    data,names,badfiles = [],[],[]
    counter = 0
    threshold = 0.47


    # Process all files in nonclustered
    available_files = os.listdir('../faces/meta/')
    available_files.remove('.DS_Store')
    
    print ("")
    print ("== Comparing Faces ==")
    print ("")

    try:
        foo = Image.open(imageloc)

        baseheight = 500
        wpercent = (baseheight / float(foo.size[1]))
        
        bsize = int((float(foo.size[0]) * float(wpercent)))

        foo = foo.resize((bsize,baseheight), Image.ANTIALIAS)

        foo = foo.rotate(-90)

        foo = foo.transpose(Image.FLIP_LEFT_RIGHT)

        foo.save(imageloc,optimize=True)

        image1 = face_recognition.load_image_file(imageloc)
        face_locations = face_recognition.face_locations(image1,model='cnn')

        
    except:
        print "Failure of Deep Learning"
        
        image1 = face_recognition.load_image_file(imageloc)
        face_locations = face_recognition.face_locations(image1,model='hog')


    try:
        y = face_recognition.load_image_file(imageloc)
        y = face_recognition.face_encodings(y, face_locations, 3)[0]

    except:
        y = []


    print ("Encoding Faces")

    for x in tqdm(range(len(available_files))):
        print available_files[x]
        data.append(pickle.load(open('../faces/meta/'+available_files[x],'rb')))
        names.append(available_files[x][:-4])

    resultant_list = []

    print ("Comparing Faces")
    for z in tqdm(range(len(data))):
        try:  
            results = face_recognition.face_distance([y], data[z])
        except:
            continue

        if results <= threshold:
            print names[z]
            copyfile("../pictures/"+names[z][1:], "../web-system/static/"+names[z][1:])
            resultant_list.append(names[z][1:])
    return resultant_list