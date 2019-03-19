import os

root = '/home/lsc/Intention_from_motion/IFM_resize/2D'

class_list = sorted(os.listdir(root))

# class_list ['Drinking', 'Passing', 'Placing', 'Pouring']
# total: 1098 train 880 test 218

# drink 300 train 240 test 60
# passing 262 train 210 test 52
# placing 283 train 226 test 57
# pouring 253 train 204 test 49

print(class_list)

# root + class + folder
list1 = sorted(os.listdir(root+ '/' + class_list[0]))
list2 = sorted(os.listdir(root+ '/' + class_list[1]))
list3 = sorted(os.listdir(root+ '/' + class_list[2]))
list4 = sorted(os.listdir(root+ '/' + class_list[3]))

train1 = [] 
test1 = []
train2 = [] 
test2 = []
train3 = [] 
test3 = []
train4 = [] 
test4 = []

p = '0'

for item in list1:
	p_new,nn = item.split('_')
	if int(p_new) < 3:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 16:
			train1.append(item)
			counter +=1
			# print('train:',item, counter-1)
		else:
			test1.append(item)
			counter +=1
			# print('test:',item, counter-1)

	else:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 15:
			train1.append(item)
			counter +=1
			# print('train:',item, counter-1)

		else:
			test1.append(item)
			counter +=1 
			# print('test:',item, counter-1)

# print(len(train1))
# print(len(test1))

# passing 262 train 210 test 52

p = '0'

for item in list2:
	p_new,nn = item.split('_')
	if int(p_new) < 8:
		if p_new != p:
			p = p_new
			counter = 1
		if int(p_new) == 1:
			if counter < 14:
				train2.append(item)
				counter +=1
				# print('train:',item, counter-1)
			else:
				test2.append(item)
				counter +=1
				# print('test:',item, counter-1)

		elif counter < 13:
			train2.append(item)
			counter +=1
			# print('train:',item, counter-1)
		else:
			test2.append(item)
			counter +=1
			# print('test:',item, counter-1)

	else:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 14:
			train2.append(item)
			counter +=1
			# print('train:',item, counter-1)

		else:
			test2.append(item)
			counter +=1 
			# print('test:',item, counter-1)

# print(len(train2))
# print(len(test2))

# placing 283 train 226 test 57

p = '0'

for item in list3:
	p_new,nn = item.split('_')
	if int(p_new) < 12:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 15:
			train3.append(item)
			counter +=1
			# print('train:',item, counter-1)
		else:
			test3.append(item)
			counter +=1
			# print('test:',item, counter-1)

	else:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 14:
			train3.append(item)
			counter +=1
			# print('train:',item, counter-1)

		else:
			test3.append(item)
			counter +=1 
			# print('test:',item, counter-1)

# print(len(train3))
# print(len(test3))

# pouring 253 train 204 test 49

p = '0'

for item in list4:
	p_new,nn = item.split('_')
	if int(p_new) < 3:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 13:
			train4.append(item)
			counter +=1
			# print('train:',item, counter-1)
		else:
			test4.append(item)
			counter +=1
			# print('test:',item, counter-1)

	else:
		if p_new != p:
			p = p_new
			counter = 1
		if counter < 14:
			train4.append(item)
			counter +=1
			# print('train:',item, counter-1)

		else:
			test4.append(item)
			counter +=1 
			# print('test:',item, counter-1)

# print(len(train4))
# print(len(test4))

train_list = train1+train2+train3+train4

print(len(train_list))

test_list = test1+test2+test3+test4

print(len(test_list))

