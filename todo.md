



# задачи которые нужно сделать:

1. когда переходим из компактного в средний режим окна то мерцание окна есть. оно видимо пересоздаётся много раз. это баг.
2. распознавание не работает по хоткею Tab+NumPad/
3. 







# проверить

1. у меня есть проблема в проекте с хоткеями. они сначала работают, но со временем они просто отключаются и перестают работать. в логах ничего не показывает. они просто выключаются и всё. я подозреваю что то со слушателем хоткеев. нужно добавить логи на счет этого слушателя. ещё есть вторая проблема с хоткеями связанная с правами админа. у моего друга хоткеи при старте даже не работают, но зато при переназначении клавиши любой , все хоткеи начинают работать. если он открывает с админ правами прогу то такой проблемы у него нету.
хоткеи пропадают после какого то времени сами собой без всяких признаков. просто в какой то момент перестают работать без специфических логов. думаю что слушатель хоткеев падает. надо исправить баг даже если придется заменить в проекте библиотеку хоткеев.



# в разработке

1. иконка в панели задач виндовс снизу пропадает иногда (плавающий баг ) когда меняем режим окна. 
2. херорейтингдиалог переписать
3. протестировать хоткеи англ-рус раскладку







# сомнительная фича
7. мне нужен хоткей чтобы я мог выбирать разные фразы и копировать выбранную в буфер обмена. можно ли сделать так чтобы я зажал какую то клавишу, и во время удержания появляется окно, которое пропадает когда я отпускаю клавишу и подтверждается выбор? а второй клавишей допустим я буду перемещаться в этом временном окне для выбора нужной фразы.
8. давай фразу "Your responsibility is not to gain healing points. Yr resp-ty is to keep your allies from dying."
8. "please healers, keep your focus on ALL allies at all times and check on them, don't let them die."
9. "The healer's job is to constantly monitor all allies to whom he has visibility access."



# рекогнишен
есть ли автоматическая разметка? я не хочу размечать вручную. тем более зачем мне это делать если герои (38шт) у меня всегда одинаковые и всегда будут в одних и тех же координатах находиться.
у меня просто есть 38 картинок 95на95 размером. и мне нужно их распознавать на скриншоте, и они всегда выглядят одинаково. поэтому мне не нужно размечать вручную их.
может ли помочь тебе этот код или нет?
   