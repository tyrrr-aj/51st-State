# Generated by Django 2.0.6 on 2018-06-20 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('s51', '0007_auto_20180620_0542'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num_passed', models.IntegerField(default=0)),
            ],
        ),
        migrations.AlterField(
            model_name='deck',
            name='kind',
            field=models.CharField(choices=[('T', 'Table'), ('H', 'Hand'), ('A', 'Agreements'), ('D', 'Discard'), ('P', 'Pile'), ('S', 'To Spare'), ('L', 'Lookup'), ('F', 'Fraction cards')], max_length=1),
        ),
    ]
